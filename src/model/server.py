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

    def __lt__(self, other):
        return self.timestamp < other.timestamp


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
