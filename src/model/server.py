from src.state_machine.state import ServerState
from datetime import datetime
import zope.event
from src.config import DISPLAY_INTERVAL, LOG_DELAY


class Request:
    def __init__(self, request_line: str):
        self._remotehost, self._rfc931, self._authuser, self.timestamp,\
            self._request, self.status, self._bytes = request_line.split(',')
        self.timestamp = int(self.timestamp)
        self.section = self._request.split(' ')[1].split('/')[1]
        self.date = datetime.utcfromtimestamp(self.timestamp).strftime('%Y-%m-%d %H:%M:%S')


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

    def __init__(self):
        self.stats_by_section = {}
        self.oldest_request = None
        self.last_request = None
        self.current_slot_times = set()

        self.delay_stats = Stats()
        self.delay_slot_times = set()

    def add_request(self, request: Request):
        stats = self
        if request.timestamp in self.delay_slot_times:
            stats = self.delay_stats

        self._store_request(stats, request)
        self._set_last_request(stats, request)
        self._update_oldest_request(stats, request)

    def _store_request(self, stats, request: Request):
        if request.section not in stats.stats_by_section:
            section_stat = self.SectionTrafficStats(request.section)
            stats.stats_by_section[request.section] = section_stat

        section_stat = stats.stats_by_section.get(request.section)
        section_stat.add_request(request)

    def _set_last_request(self, stats, request: Request):
        if stats.last_request:
            if request.timestamp > stats.last_request.timestamp:
                stats.last_request = request
        else:
            stats.last_request = request

    def _update_oldest_request(self, stats, request: Request):
        """
        The order of the logs in the file is not guarantee so
        we need  to make sure to update the oldest request if the
        new request is oldest.
        """
        if not stats.oldest_request:
            stats.set_oldest(request)
            return

        if request.timestamp < stats.oldest_request.timestamp:
            stats.set_oldest(request)

    def set_oldest(self,stats, request: Request):
        stats.current_slot_times.clear()
        last_timestamp = None
        stats.current_slot_times = set()
        stats.delay_slot_times = set()

        for second in range(DISPLAY_INTERVAL):
            stats.current_slot_times.add(request.timestamp + second)
            last_timestamp = request.timestamp + second

        for second in range(1, LOG_DELAY):
            stats.delay_slot_times.add(last_timestamp + second)

        stats.current_slot_times.update(stats.delay_slot_times)
        print('DELAY', stats.delay_slot_times)
        print('CURRENT', stats.current_slot_times)

        stats.oldest_request = request


class Observable:
    def add_subscriber(self, function):
        zope.event.subscribers.append(function)

    def notify(self, event):
        zope.event.notify(event)


class ServerStateMachine(Observable):
    def __init__(self):
        self._server_state = ServerState.GOOD

    def set_server_state(self, state):
        self._server_state = state

    def get_server_state(self):
        return self._server_state
