from src.state_machine.state import ServerState
from datetime import datetime
import zope.event


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

    def add_request(self, request: Request):
        if request.section not in self.stats_by_section:
            section_stat = SectionTrafficStats(request.section)
            stats[request.section] = section_stat

        section_stat = stats.get(request.section)
        section_stat.add_request(request)

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
