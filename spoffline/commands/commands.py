import importlib
import os.path

import click
from rich.panel import Panel

from spoffline.console import console
from spoffline.constants import SPOFFLINE_NAME, SPOFFLINE_VERSION, SPOFFLINE_VERSION_NAME
from spoffline.helpers import project_path


class Commands(click.MultiCommand):
    def __call__(self, *args, **kwargs):
        version = f'v{SPOFFLINE_VERSION} [{SPOFFLINE_VERSION_NAME}]'

        click.clear()

        console.print(Panel(
            f'[white]{SPOFFLINE_NAME}',
            subtitle=f'[white]{version}',
            width=len(version) * 2,
            padding=1,
            style='green'
        ), justify='center')
        console.print('\n')

        super().__call__(*args, **kwargs)

    @property
    def commands_path(self):
        return os.path.join(project_path, 'spoffline/commands')

    def list_commands(self, _):
        commands = []

        for filename in os.listdir(self.commands_path):
            if filename.endswith('.py') and filename not in ['__init__.py', 'commands.py']:
                commands.append(filename[:-3])

        return commands

    def get_command(self, ctx, command):
        commands = self.list_commands(ctx)

        if command not in commands:
            return None

        command_class = importlib.import_module(f'spoffline.commands.{command}')

        if hasattr(command_class, 'cli'):
            return command_class.cli

        return None
