from src.config import SCREEN_INTERVAL, TOP_SECTIONS
from src.event.event import StateChangeEvent, NewRequestsEvent
from src.model.server import Observable, Request
from collections import deque
from columnar import columnar
from typing import List, Dict
import click
import heapq
import time


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
        self._alarms_new_data_queue = deque([])
        self._progress_bar = [second for second in reversed(range(1, SCREEN_INTERVAL + 1))]

    def on_new_data(self, event: NewRequestsEvent):
        print('NEW REQUESTS EVENT: ' + str(len(event.requests)))

        stats = self.Stats(event.requests)
        self._new_data_queue.append(stats.get_top_sections())
        self._draw()

    def on_server_state_change(self, event: StateChangeEvent):
        pass

    def _draw(self):
        click.clear()

        traffic_stats = self._new_data_queue.popleft()

        if not traffic_stats:
            click.secho('No HTTP requests', fg='green')
            return

        click.secho('*****LOG MONITOR*******', fg='green')
        table = []
        for traffic_stat in traffic_stats:
            row = [traffic_stat.section, traffic_stat.total_hits]
            table.append(row)

        table = columnar(table, no_borders=True)
        click.secho(str(table), fg='green')

        self._display_progress_bar()

        # if alert_message:
        #     click.secho(alert_message, fg='red')

    def _display_progress_bar(self):
        with click.progressbar(self._progress_bar) as bar:
            for x in bar:
                print(f"new stats in ({x})...")
                time.sleep(1)


class TTLCache:
    """
    This class will handle a TTL list Where the values are timestamps

    - We'll store UNIX timestamps, reading from a file that may not respect the order
    to fix this issue let's use a Min HEAP where the root will be always the oldest
    request, this will give us O(log N) time complexity for resize instead of the
    O(1) for normal list but this will give us 100% accuracy for triggering alarms


    The HEAP will be re-size on LEN and APPEND checking the root timestamp (Oldest or min timestamp)
    - On APPEND -> will compare the head with the new timestamp and remove from head
    - On LEN -> will compare the head with  the tail and remove from head
    """
    def __init__(self, ttl: int):
        self.ttl = ttl
        self._heap = []

    def append(self, unix_timestamp: int):
        self._resize(unix_timestamp)
        heapq.heappush(self._heap, unix_timestamp)

    def __len__(self):
        return len(self._heap)

    def _resize(self, timestamp_to_compare: int):
        if self._is_empty():
            return

        needs_resize = True

        while needs_resize:
            needs_resize = False
            head = self._get_head()
            diff = timestamp_to_compare - head
            if diff > self.ttl:
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
    This class will store requests in a MIN heap
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
