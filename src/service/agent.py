from src.model.server import Request, SectionTrafficStats, Observable, ServerStateMachine
from src.config import ALERT_INTERVAL, DISPLAY_INTERVAL, THRESHOLD, TOP_SECTIONS, LOG_DELAY
from twisted.internet import task, reactor
from src.utils.utils import TTLCache
from src.event.event import NewDataEvent
from typing import List
import threading
import heapq
import time


class Agent(Observable):
    """
    Agent will be reading the log file and calling
    """

    def __init__(self, file_path: str, server_state_machine: ServerStateMachine):
        self.server_state_machine = server_state_machine
        self._interval_cache = TTLCache(ttl=1)
        self._stats = {}
        self._delay_stats = {}
        self._oldest_request = None
        self._current_slot_times = set()
        self._delay_slot_times = set()
        self._file_path = file_path
        self._alert_message = ''
        self._agent_daemon = threading.Thread(target=self._read_file)
        self._high_traffic_recovered = True
        self._last_request = None

    def run(self):
        self._agent_daemon.start()

    def _read_file(self):
        with open(self._file_path, "r") as log_file:
            log_lines = self._follow(log_file)
            header = next(log_lines)

            for log_line in log_lines:
                self._process_request(log_line)

    def _follow(self, log_file):
        while True:
            line = log_file.readline()
            if not line:
                time.sleep(0.1)
                continue
            yield line

    def _process_request(self, log_line: str):
        request = Request(log_line)
        print(request.date)
        self._interval_cache.append(request.timestamp)

        self._set_last_request(request)
        self._update_oldest_request(request)
        self._fire_new_data_event()
        self._add_request_to_stats(request)

    def _add_request_to_stats(self, request: Request):
        stats = self._stats
        if request.timestamp in self._delay_slot_times:
            stats = self._delay_stats
            print('Added to delay '+ str(request.date))

        if request.section not in stats:
            section_stat = SectionTrafficStats(request.section)
            stats[request.section] = section_stat

        section_stat = stats.get(request.section)
        section_stat.add_request(request)


    def _set_last_request(self, request: Request):
        if self._last_request:
            if request.timestamp > self._last_request.timestamp:
                self._last_request = request
        else:
            self._last_request = request

    def _update_oldest_request(self, request: Request):
        """
        The order of the logs in the file is not guarantee so
        we need  to make sure to update the oldest request if the
        new request is oldest.
        """
        if not self._oldest_request:
            self._set_oldest(request)
            return

        if request.timestamp < self._oldest_request.timestamp:
            self._set_oldest(request)

    def _set_oldest(self, request: Request):
        self._current_slot_times.clear()
        last_timestamp = None
        self._current_slot_times = set()
        self._delay_slot_times = set()

        for second in range(DISPLAY_INTERVAL):
            self._current_slot_times.add(request.timestamp + second)
            last_timestamp = request.timestamp + second

        for second in range(1, LOG_DELAY):
            self._delay_slot_times.add(last_timestamp + second)

        self._current_slot_times.update(self._delay_slot_times)
        print('DELAY', self._delay_slot_times)
        print('CURRENT', self._current_slot_times)

        self._oldest_request = request

    def _fire_new_data_event(self):
        if not self._should_send_new_data():
            return

        event = NewDataEvent(self._get_top_sections())
        self.notify(event)
        self._reset_stats()

    def _reset_stats(self):
        self._stats = self._delay_stats
        self._delay_stats = {}
        self._set_oldest(self._last_request)

    def _should_send_new_data(self):
        if self._last_request.timestamp not in self._current_slot_times:
            print("NEXT!! " + str(self._last_request.timestamp))
        return True if self._last_request.timestamp not in self._current_slot_times else False

    def _get_top_sections(self) -> List[SectionTrafficStats]:
        sections = [stat for stat in self._stats.values()]
        heapq.heapify(sections)

        top_sections = []
        top_k = TOP_SECTIONS if len(sections) > TOP_SECTIONS else len(sections)

        for i in range(top_k):
            top_sections.append(heapq.heappop(sections))

        return top_sections

    def _check_state_machine(self) -> str:
        alert_message = ""
        if self._is_high_traffic() and self._high_traffic_recovered:
            alert_message = f"High traffic generated an alert - hits =" \
                            f" {self._get_average_hits_by_second()}, triggered at {self._last_request.date}"
            self._high_traffic_recovered = False
        elif not self._is_high_traffic():
            self._high_traffic_recovered = True

        return alert_message

    def _is_high_traffic(self) -> bool:
        return self._get_average_hits_by_second() >= THRESHOLD

    def _get_average_hits_by_second(self):
        return len(self._interval_cache) / ALERT_INTERVAL
