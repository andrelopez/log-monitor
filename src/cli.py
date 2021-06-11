import click
from src.service.agent import Agent
import os
from src.utils.utils import Screen
from src.model.server import ServerStateMachine


@click.command()
@click.argument("file", type=str, required=True)
def cli(file):

    if not os.path.exists(file):
        click.secho('File not found', fg='red')
        return

    screen = Screen()

    server_state_machine = ServerStateMachine()
    agent = Agent(file, server_state_machine)

    agent.add_state_change_subscriber(screen.on_server_state_change)
    agent.add_data_subscriber(screen.on_new_data)

    agent.run()


