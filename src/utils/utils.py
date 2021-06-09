from columnar import columnar
from typing import List
from src.model.server import SectionTrafficStats
import click
import heapq
from src.config import DISPLAY_INTERVAL
from src.event.event import NewDataEvent, StateChangeEvent
from collections import deque
import time


class Screen:
    def __init__(self):
        self._new_data_queue = deque([])
        self._alarms_new_data_queue = deque([])
        self._progress_bar = [second for second in reversed(range(1, DISPLAY_INTERVAL +1))]

    def on_new_data(self, event: NewDataEvent):
        print('NEW DATA EVENT: ' + str(len(event.traffic_stats)))
        self._new_data_queue.append(event.traffic_stats)
        self._draw()

    def on_server_state_change(self, event: StateChangeEvent):
        pass

    def _draw(self):
        if not self._new_data_queue:
            click.secho('No HTTP requests', fg='green')
            return

        traffic_stats = self._new_data_queue.popleft()
        click.secho('*****LOG MONITOR*******', fg='green')
        table = []
        for traffic_stat in traffic_stats:
            row = [traffic_stat.section, traffic_stat.total_hits]
            table.append(row)

        table = columnar(table, no_borders=True)
        click.secho(str(table), fg='green')


        click.clear()

        #self._display_progress_bar()

        # if alert_message:
        #     click.secho(alert_message, fg='red')

    def _display_progress_bar(self):
        with click.progressbar(self._progress_bar) as bar:
            for x in bar:
                print(f"new stats in ({x})...")
                time.sleep(1)


class TTLCache:
    """
    This class will handle a TTL list Where the values are timestamps

    - We'll store UNIX timestamps, reading from a file that may not respect the order
    to fix this issue let's use a Min HEAP where the root will be always the oldest
    request, this will give us O(log N) time complexity for resize instead of the
    O(1) for normal list but this will give us 100% accuracy for triggering alarms


    The HEAP will be re-size on LEN and APPEND checking the root timestamp (Oldest or min timestamp)
    - On APPEND -> will compare the head with the new timestamp and remove from head
    - On LEN -> will compare the head with  the tail and remove from head
    """
    def __init__(self, ttl: int):
        self.ttl = ttl
        self._heap = []

    def append(self, unix_timestamp: int):
        self._resize(unix_timestamp)
        heapq.heappush(self._heap, unix_timestamp)

    def __len__(self):
        return len(self._heap)

    def _resize(self, timestamp_to_compare: int):
        if self._is_empty():
            return

        needs_resize = True

        while needs_resize:
            needs_resize = False
            head = self._get_head()
            diff = timestamp_to_compare - head
            if diff > self.ttl:
                self._remove_oldest()
                needs_resize = True

            if self._is_empty():
                break

    def _get_head(self):
        return self._heap[0]

    def _is_empty(self):
        return len(self._heap) == 0

    def _remove_oldest(self):
        heapq.heappop(self._heap)