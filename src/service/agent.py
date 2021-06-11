from src.model.server import Request, ServerStateMachine
from src.config import ALERT_INTERVAL, DISPLAY_INTERVAL, LOG_DELAY, CSV_COLUMNS
from src.utils.utils import TTLIntervalCache, TTLRequestCache
import threading
import time


class Agent:
    """
    Agent will be reading the log file and calling
    """

    def __init__(self, file_path: str, server_state_machine: ServerStateMachine):
        self.server_state_machine = server_state_machine
        self._interval_cache = TTLIntervalCache(ALERT_INTERVAL, LOG_DELAY, self.server_state_machine)
        self.requests = TTLRequestCache(DISPLAY_INTERVAL, LOG_DELAY)

        self._file_path = file_path
        self._alert_message = ''
        self._agent_daemon = threading.Thread(target=self._read_file)
        self._high_traffic_recovered = True

    def run(self):
        self._agent_daemon.start()

    def add_subscriber(self, function):
        self.requests.add_subscriber(function)

    def _read_file(self):
        with open(self._file_path, "r") as log_file:
            log_lines = self._follow(log_file)
            header = next(log_lines)

            for log_line in log_lines:
                self._process_request(log_line)

    def _follow(self, log_file):
        while True:
            line = log_file.readline()
            if not line:
                time.sleep(0.1)
                continue
            yield line

    def _process_request(self, log_line: str):
        if not self._is_valid_line(log_line):
            return

        request = Request(log_line)
        self.requests.append(request)
        self._interval_cache.append(request.timestamp)

    def _is_valid_line(self, log_line: str):
        return True if len(log_line.split(',')) == CSV_COLUMNS else False
