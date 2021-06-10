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
        self.fire_event_slot_times = set()

        self.delay_stats = {}
        self.delay_slot_times = set()
        self.delay_oldest_request = None
        self.delay_last_request = None

    def add_request(self, request: Request):
        if not self._is_valid(request):
            print('Ignoring we should raise data event')
            return

        stats = self.stats_by_section
        if request.timestamp in self.delay_slot_times:
            stats = self.delay_stats
            self._set_delay_last_request(request)
            self._set_delay_oldest_request(request)

        self._store_request(stats, request)
        self._set_last_request(request)
        self._update_oldest_request(request)

    def _is_valid(self, request: Request):
        """
        Request is not in the out of range
        """
        if not self.current_slot_times:
            return True

        return True if request.timestamp <= max(self.delay_slot_times) else False

    def _store_request(self, stats, request: Request):
        if request.section not in stats:
            section_stat = self.SectionTrafficStats(request.section)
            stats[request.section] = section_stat

        section_stat = stats.get(request.section)
        section_stat.add_request(request)

    def _set_last_request(self, request: Request):
        if self.last_request:
            if request.timestamp > self.last_request.timestamp:
                self.last_request = request
        else:
            self.last_request = request

    def _set_delay_last_request(self, request: Request):
        if self.delay_last_request:
            if request.timestamp > self.delay_last_request.timestamp:
                self.delay_last_request = request
        else:
            self.delay_last_request = request

    def _set_delay_oldest_request(self, request: Request):
        if not self.delay_oldest_request:
            self.delay_oldest_request = request
            return

        if request.timestamp < self.delay_oldest_request.timestamp:
            self.delay_oldest_request = request

    def _update_oldest_request(self, request: Request):
        """
        The order of the logs in the file is not guarantee so
        we need  to make sure to update the oldest request if the
        new request is oldest.
        """
        if not self.oldest_request:
            self.set_oldest(request)
            return

        if request.timestamp < self.oldest_request.timestamp:
            self.set_oldest(request)

    def set_oldest(self, request: Request):
        self.current_slot_times.clear()
        self.delay_slot_times = set()
        last_timestamp = None

        for second in range(DISPLAY_INTERVAL):
            self.current_slot_times.add(request.timestamp + second)
            last_timestamp = request.timestamp + second

        for second in range(1, LOG_DELAY):
            self.delay_slot_times.add(last_timestamp + second)

        self.current_slot_times.update(self.delay_slot_times)
        print('DELAY', self.delay_slot_times)
        print('CURRENT', self.current_slot_times)

        self.oldest_request = request

    def should_raise_event(self, request: Request):
        if not self.current_slot_times:
            return False

        if request.timestamp not in self.current_slot_times:
            print("NEXT!! " + str(request.timestamp))
        return False if request.timestamp in self.current_slot_times else True

    def reset_stats(self):
        self.stats_by_section = self.delay_stats
        self.delay_stats = {}
        if self.delay_oldest_request:
            self.set_oldest(self.delay_oldest_request)
        else:
            self.oldest_request = None

        if self.delay_last_request:
            self._set_last_request(self.delay_last_request)
        else:
            self.oldest_request = None

        self.delay_oldest_request = None
        self.delay_last_request = None


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
