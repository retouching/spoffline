import importlib
import os.path

import click

from spoffline.helpers import project_path


class Commands(click.MultiCommand):
    @property
    def commands_path(self):
        return os.path.join(project_path, 'ffdevine/commands')

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

        command_class = importlib.import_module(f'ffdevine.commands.{command}')

        if hasattr(command_class, 'cli'):
            return command_class.cli

        return None
