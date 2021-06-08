from enum import Enum, auto


class ServerState(Enum):
    GOOD = auto()
    HIGH_TRAFFIC = auto()