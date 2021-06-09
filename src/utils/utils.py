from columnar import columnar
from typing import List
from src.model.server import SectionTrafficStats
import click
import heapq


class Screen:
    def __init__(self):
        self.last_data = []

    def on_new_data(self, event):

        pass

    def on_server_state_change(self, event):
        pass

    def _draw(self, traffic_stats: List[SectionTrafficStats], alert_message: str):
        click.clear()
        click.secho('*****LOG MONITOR*******', fg='green')
        if not traffic_stats:
            click.secho('No HTTP requests', fg='green')
            return

        table = []
        for traffic_stat in traffic_stats:
            row = [traffic_stat.section, traffic_stat.total_hits]
            table.append(row)

        table = columnar(table, no_borders=True)
        click.secho(str(table), fg='green')

        if alert_message:
            click.secho(alert_message, fg='red')


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