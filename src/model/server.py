from src.state_machine.state import ServerState
from src.event.event import StateChangeEvent
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

    def set_server_state(self, new_state, average_hits, unix_timestamp):
        self._validate_events(new_state, average_hits, unix_timestamp)
        self._server_state = new_state

    def get_server_state(self):
        return self._server_state

    def _validate_events(self, new_state, average_hits, unix_timestamp):
        if self._is_state_change_to_high_traffic(new_state):
            self._trigger_on_high_traffic_event(average_hits, unix_timestamp)

        if self._is_state_change_to_good_traffic(new_state):
            self._trigger_on_good_traffic_event(average_hits, unix_timestamp)

    def _trigger_on_high_traffic_event(self, average_hits, unix_timestamp):
        self.notify(StateChangeEvent(ServerState.HIGH_TRAFFIC, average_hits, unix_timestamp))

    def _trigger_on_good_traffic_event(self, average_hits, unix_timestamp):
        self.notify(StateChangeEvent(ServerState.GOOD, average_hits, unix_timestamp))

    def _is_state_change_to_high_traffic(self, new_state):
        return self._server_state == ServerState.GOOD and new_state == ServerState.HIGH_TRAFFIC

    def _is_state_change_to_good_traffic(self, new_state):
        return self._server_state == ServerState.HIGH_TRAFFIC and new_state == ServerState.GOOD

