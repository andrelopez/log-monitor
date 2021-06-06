import click
from src.service.agent import Agent
import os
import pandas as pd
import time

class Context:
    def __init__(self, file: str):
        self.agent = Agent(file)


@click.command()
@click.argument("file", type=str, required=True)
@click.pass_context
def cli(ctx, file):

    if not os.path.exists(file):
        click.secho('File not found', fg='red')
        return

    ctx.obj = Context(file)
    ctx.obj.agent.run()


