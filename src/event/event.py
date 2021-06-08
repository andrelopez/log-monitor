from src.model.server import ServerState, SectionTrafficStats
from typing import List


class NewDataEvent:
    def __init__(self, traffic_stats: List[SectionTrafficStats]):
        self.traffic_stats = traffic_stats


class StateChangeEvent:
    def __init__(self, server_state: ServerState, traffic_stats: List[SectionTrafficStats]):
        self.server_state = server_state
        self.traffic_stats = traffic_stats



