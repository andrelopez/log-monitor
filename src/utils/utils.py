from src.config import SCREEN_INTERVAL, TOP_SECTIONS, THRESHOLD, ALERT_INTERVAL
from src.event.event import StateChangeEvent, NewRequestsEvent
from src.model.server import Observable, Request, ServerStateMachine
from src.state_machine.state import ServerState
from collections import deque
from columnar import columnar
from typing import List, Dict
import click
import heapq
import time
import threading
from datetime import datetime


class Screen:
    class Stats:
        class SectionTrafficStats:
            def __init__(self, section: str):
                self.hits_by_status = {}
                self.section = section
                self.total_hits = 0

            def add_request(self, request: Request):
                self.hits_by_status.setdefault(request.status, 0)
                self.hits_by_status[request.status] += 1
                self.total_hits += 1

            def __lt__(self, other):
                return self.total_hits > other.total_hits

        def __init__(self, requests: List[Request]):
            self._requests = requests
            self.from_request = requests[0] if self._requests else None
            self.to_request = requests[-1] if self._requests else None
            self._top_sections = []
            self._process_stats()

        def get_top_sections(self) -> List[SectionTrafficStats]:
            return self._top_sections

        def _process_stats(self):
            stats = {}

            for request in self._requests:
                if request.section not in stats:
                    section_stat = self.SectionTrafficStats(request.section)
                    stats[request.section] = section_stat

                section_stat = stats.get(request.section)
                section_stat.add_request(request)

            self._get_top_sections(stats)

        def _get_top_sections(self, stats: Dict):
            sections = [stat for stat in stats.values()]
            heapq.heapify(sections)

            self._top_sections = []
            top_k = TOP_SECTIONS if len(sections) > TOP_SECTIONS else len(sections)

            for i in range(top_k):
                self._top_sections.append(heapq.heappop(sections))

    def __init__(self):
        self._new_data_queue = deque([])
        self._alarms_queue = deque([])
        self._progress_bar = [second for second in reversed(range(1, SCREEN_INTERVAL + 1))]
        self._last_alarm = None
        self._server_status = ServerState.GOOD
        self._draw_thread = threading.Thread(target=self._draw)
        self._draw_thread.start()

    def on_new_data(self, event: NewRequestsEvent):
        if not isinstance(event, NewRequestsEvent):
            return

        stats = self.Stats(event.requests)
        self._new_data_queue.append(stats)

    def on_server_state_change(self, event: StateChangeEvent):
        if not isinstance(event, StateChangeEvent):
            return

        self._alarms_queue.append(event)

    def _draw(self):
        while True:
            click.clear()
            if self._new_data_queue:
                self._print_data()
                continue

            click.secho('No HTTP requests', fg='green')
            time.sleep(0.5)

    def _print_data(self):
        stats = self._new_data_queue.popleft()
        traffic_stats = stats.get_top_sections()

        alert_message = None
        color_alert_message = 'blue'
        if not self._last_alarm and self._alarms_queue:
            self._last_alarm = self._alarms_queue.popleft()

        if self._last_alarm:
            if self._last_alarm.timestamp < stats.to_request.timestamp:
                alert_message = self._get_alarm_message(self._last_alarm)
                self._server_status = self._last_alarm.server_state
                if self._last_alarm.server_state == ServerState.HIGH_TRAFFIC:
                    color_alert_message = 'red'

                self._last_alarm = None

        with click.progressbar(self._progress_bar) as bar:
            for x in bar:
                print(f" for new interval ...")
                if not traffic_stats:
                    click.secho('No HTTP requests', fg='green')
                    return

                click.secho('*****LOG MONITOR*******', fg='green')
                click.secho(f'From: {stats.from_request.date}', fg='green')
                click.secho(f'To: {stats.to_request.date}', fg='green')
                color_server_status = 'blue'
                if self._server_status == ServerState.HIGH_TRAFFIC:
                    color_server_status = 'red'
                click.secho(f'Sever Status: {self._server_status.name}', fg=color_server_status)
                table = []
                for traffic_stat in traffic_stats:
                    row = [traffic_stat.section, traffic_stat.total_hits]
                    table.append(row)

                table = columnar(table, no_borders=True)
                click.secho(str(table), fg='green')

                if alert_message:
                    click.secho(alert_message, fg=color_alert_message)
                time.sleep(1)
                click.clear()

    def _get_alarm_message(self, event: StateChangeEvent) -> str:
        message = ""
        date_formatted = datetime.utcfromtimestamp(event.timestamp).strftime('%Y-%m-%d %H:%M:%S')

        if event.server_state == ServerState.HIGH_TRAFFIC:
            message = f"High Traffic generated an alert - hits {event.average_hits:.2f} triggered at {date_formatted}"
        elif event.server_state == ServerState.GOOD:
            message = f"Server recovered alert at {date_formatted}"

        return message

class TTLIntervalCache(Observable):
    """
    This class will handle a TTL list Where the values are timestamps

    - We'll store UNIX timestamps, reading from a file that may not respect the order
    to fix this issue let's use a Min HEAP where the root will be always the oldest
    request, this will give us O(log N) time complexity for resize instead of the
    O(N) for normal list and this will give us 100% accuracy for triggering alarms


    The HEAP will re-size on LEN and APPEND checking the root timestamp (Oldest or min timestamp)
    - On APPEND -> will compare the head with the new timestamp and remove from head
    """
    def __init__(self, ttl: int, log_delay: int, server_state_machine: ServerStateMachine):
        self.ttl = ttl
        self.log_delay = log_delay
        self.server_state_machine = server_state_machine
        self._heap = []
        self._delay_queue = deque([])
        self._window_size = self.ttl - 1

    def append(self, unix_timestamp: int):
        if not self._is_empty() and self._is_outside_alert_interval(unix_timestamp):
            self._handle_delay_queue(unix_timestamp)
            return

        self._insert(unix_timestamp)

    def _insert(self, unix_timestamp: int):
        self._resize(unix_timestamp)
        heapq.heappush(self._heap, unix_timestamp)
        self._set_state_machine(unix_timestamp)

    def _handle_delay_queue(self, unix_timestamp):
        """
        This method will store any timestamp outside the (ALERT_INTERVAL + LOG_DELAY) window in a queue
        once a timestamp > (ALERT_INTERVAL + LOG_DELAY) we'll restore all the values in the delay queue
        one by one into our MIN HEAP calling the insert method that will check also the machine state.
        """
        self._delay_queue.append(unix_timestamp)

        if self._is_outside_delay_interval(unix_timestamp):
            while self._delay_queue:
                self._insert(self._delay_queue.popleft())

    def _is_outside_alert_interval(self, unix_timestamp: int) -> bool:
        return unix_timestamp > self._get_oldest() + self._window_size

    def _is_outside_delay_interval(self, unix_timestamp: int) -> bool:
        return unix_timestamp > self._get_oldest() + (self._window_size + self.log_delay)

    def _set_state_machine(self, unix_timestamp):
        if self._is_high_traffic():
            self.server_state_machine.set_server_state(ServerState.HIGH_TRAFFIC, self._get_average_hits_by_second(), unix_timestamp)
        else:
            self.server_state_machine.set_server_state(ServerState.GOOD, self._get_average_hits_by_second(), unix_timestamp)

    def _is_high_traffic(self) -> bool:
        return self._get_average_hits_by_second() >= THRESHOLD

    def _get_average_hits_by_second(self):
        return len(self._heap) / ALERT_INTERVAL

    def _get_oldest(self):
        return self._heap[0]

    def _resize(self, timestamp_to_compare: int):
        if self._is_empty():
            return

        needs_resize = True

        while needs_resize:
            needs_resize = False
            head = self._get_head()
            diff = timestamp_to_compare - head
            if diff > self._window_size:
                self._remove_oldest()
                needs_resize = True

            if self._is_empty():
                break

    def _get_head(self):
        return self._heap[0]

    def _is_empty(self):
        return len(self._heap) == 0

    def _remove_oldest(self):
        heapq.heappop(self._heap)


class TTLRequestCache(Observable):
    """
    This class will store requests in a MIN heap data structure
    the oldest request will be at the root
    and to fix order requests from the log file
    we we'll fire the event of new data after a new request
    is higher than DISPLAY_INTERVAL + LOG_DELAY
    the LOG_DELAY can be updated on the config file as needed
    """
    def __init__(self, ttl: int, log_delay: int):
        self.ttl = ttl
        self.log_delay = log_delay
        self._heap = []

    def append(self, request: Request):
        self._resize(request)
        heapq.heappush(self._heap, request)

    def __len__(self):
        return len(self._heap)

    def _resize(self, new_request: Request):
        if self._is_empty():
            return

        head = self._get_head()
        diff = new_request.timestamp - head.timestamp

        if diff > (self.ttl + self.log_delay):
            self._trigger_new_data_event()

    def _get_head(self):
        return self._heap[0]

    def _is_empty(self):
        return len(self._heap) == 0

    def _trigger_new_data_event(self):
        requests = self._get_requests()
        event = NewRequestsEvent(requests)
        self.notify(event)

    def _get_requests(self):
        requests = []
        oldest = self._get_head()
        while self._heap:
            current_request = self._get_head()
            if current_request.timestamp > oldest.timestamp + self.ttl - 1:
                break

            heapq.heappop(self._heap)
            requests.append(current_request)

        return requests
