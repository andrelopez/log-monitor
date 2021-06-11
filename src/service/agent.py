from src.model.server import Request, ServerStateMachine
from src.config import ALERT_INTERVAL, DISPLAY_INTERVAL, LOG_DELAY, CSV_COLUMNS
from src.utils.utils import TTLIntervalCache, TTLRequestCache
import threading


class Agent:
    """
    The Agent will receive a filepath and a server_state_machine as parameters
    The run method should be called  to start the agent, it will read the file and stop when reach the last line,
    Subscribers can listen the following events:
        - add_data_subscriber -> it will notify with a NewRequestsEvent
        - add_state_change_subscriber -> it will notify with a StateChangeEvent

    The agent will use a MIN HEAP data structure to handle the alarm intervals and requests
    please take a look to the TTLIntervalCache and TTLRequestCache classes respectively
    """

    def __init__(self, file_path: str, server_state_machine: ServerStateMachine):
        self.server_state_machine = server_state_machine
        self._interval_cache = TTLIntervalCache(ALERT_INTERVAL, LOG_DELAY, self.server_state_machine)
        self.requests = TTLRequestCache(DISPLAY_INTERVAL, LOG_DELAY)

        self._file_path = file_path
        self._alert_message = ''
        self._agent_thread = threading.Thread(target=self._read_file)
        self._high_traffic_recovered = True

    def run(self):
        self._agent_thread.start()

    def add_data_subscriber(self, function):
        self.requests.add_subscriber(function)

    def add_state_change_subscriber(self, function):
        self.server_state_machine.add_subscriber(function)

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
                # end of file, we can set continue instead of break if we want to wait for new lines in real time
                break
            yield line

    def _process_request(self, log_line: str):
        if not self._is_valid_line(log_line):
            return

        request = Request(log_line)
        self.requests.append(request)
        self._interval_cache.append(request.timestamp)

    def _is_valid_line(self, log_line: str):
        return True if len(log_line.split(',')) == CSV_COLUMNS else False
