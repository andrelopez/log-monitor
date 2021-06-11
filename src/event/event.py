class NewRequestsEvent:
    def __init__(self, requests):
        self.requests = requests


class StateChangeEvent:
    def __init__(self, server_state, average_hits: float, timestamp: int):
        self.server_state = server_state
        self.average_hits = average_hits
        self.timestamp = timestamp



