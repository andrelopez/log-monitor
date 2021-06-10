from src.model.server import ServerState, Request
from typing import List


class NewRequestsEvent:
    def __init__(self, requests: List[Request]):
        self.requests = requests


class StateChangeEvent:
    def __init__(self, server_state: ServerState):
        self.server_state = server_state



