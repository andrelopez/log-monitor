from columnar import columnar
from typing import List
from src.model.section_traffic_stat import SectionTrafficStats
import click


def draw(traffic_stats: List[SectionTrafficStats], alert_message: str):
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