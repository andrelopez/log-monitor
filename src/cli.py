import click
from src.service.agent import Agent
import os
import pandas as pd
import time
from src.model.server import ServerStateMachine
from src.utils.utils import Screen


@click.command()
@click.argument("file", type=str, required=True)
def cli(file):

    if not os.path.exists(file):
        click.secho('File not found', fg='red')
        return

    screen = Screen()

    server_state_machine = ServerStateMachine()
    server_state_machine.add_subscriber(screen.on_server_state_change)

    agent = Agent(file, server_state_machine)
    agent.add_subscriber(screen.on_new_data)

    agent.run()


