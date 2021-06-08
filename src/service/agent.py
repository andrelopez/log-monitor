from src.model.server import Request, SectionTrafficStats, Observable, ServerStateMachine
from src.config import ALERT_INTERVAL, DISPLAY_INTERVAL, THRESHOLD, TOP_SECTIONS
from twisted.internet import task, reactor
from cachetools import TTLCache
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
        self._interval_cache = TTLCache(maxsize=float('inf'), ttl=ALERT_INTERVAL)
        self._stats = {}
        self._file_path = file_path
        self._alert_message = ''
        self._agent_daemon = threading.Thread(target=self._read_file, daemon=True)
        self._high_traffic_recovered = True
        self._last_request_date = None

    def run(self):
        self._agent_daemon.start()

        update_stats = task.LoopingCall(self._fire_new_data_event)
        update_stats.start(DISPLAY_INTERVAL)

        reactor.run()

    def _fire_new_data_event(self):
        event = NewDataEvent(self._get_top_sections())
        self.notify(event)

    def _get_top_sections(self) -> List[SectionTrafficStats]:
        if not self._last_stats:
            return []

        sections = [stat for stat in self._last_stats.values()]
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
                            f" {self._get_average_hits_by_second()}, triggered at {self._last_request_date}"
            self._high_traffic_recovered = False
        elif not self._is_high_traffic():
            self._high_traffic_recovered = True

        return alert_message

    def _is_high_traffic(self) -> bool:
        return self._get_average_hits_by_second() >= THRESHOLD

    def _get_average_hits_by_second(self):
        return len(self._interval_cache) / ALERT_INTERVAL

    def _read_file(self):
        with open(self._file_path, "r") as log_file:
            log_lines = self._follow(log_file)
            header = next(log_lines)

            for request in log_lines:
                self._process_request(request)
                time.sleep(0.2)

    def _process_request(self, request: str):
        request = Request(request)
        self._interval_cache[time.time()] = True
        self._last_request_date = request.date

        if request.section not in self._stats:
            traffic_stat = SectionTrafficStats(request.section)
            self._stats[request.section] = traffic_stat

        traffic_stat = self._stats[request.section]
        traffic_stat.add_request(request)

    def _follow(self, log_file):
        while True:
            line = log_file.readline()
            if not line:
                time.sleep(0.1)
                continue
            yield line
