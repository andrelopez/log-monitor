from src.model.server import Request, SectionTrafficStats, Observable, ServerStateMachine
from src.config import ALERT_INTERVAL, DISPLAY_INTERVAL, THRESHOLD, TOP_SECTIONS
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
        self._file_path = file_path
        self._alert_message = ''
        self._agent_daemon = threading.Thread(target=self._read_file, daemon=True)
        self._high_traffic_recovered = True
        self._new_data_event_start = None
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
        self._interval_cache.append(request.timestamp)

        if request.section not in self._stats:
            section_stat = SectionTrafficStats(request.section)
            self._stats[request.section] = section_stat

        section_stat = self._stats.get(request.section)
        section_stat.add_request(request)

        self._set_last_request(request)

    def _set_last_request(self, request: Request):
        if self._last_request:
            diff = abs(request.timestamp - self._last_request.timestamp)
            time.sleep(diff)
            if request.timestamp > self._last_request.timestamp:
                self._last_request = request
        else:
            self._last_request = request

    def _review_display_interval(self, request: Request):
        if not self._new_data_event_start:
            self._new_data_event_start = request.timestamp

    def _fire_new_data_event(self):
        event = NewDataEvent(self._get_top_sections())
        self.notify(event)

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
