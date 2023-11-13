import os.path

import yaml

from spoffline.helpers.exceptions import ConfigurationException
from spoffline.helpers.paths import DefaultPaths


class Configuration:
    def __init__(self, email, password):
        self.email = email
        self.password = password

    @staticmethod
    def get_config_path():
        return os.path.join(DefaultPaths.get_root_path(), 'config.yml')

    @staticmethod
    def load():
        if not os.path.exists(Configuration.get_config_path()):
            raise ConfigurationException('You must create a configuration before load it')

        with open(Configuration.get_config_path(), 'r') as f:
            config = yaml.safe_load(f)

        if 'email' not in config or 'password' not in config:
            raise ConfigurationException('Malformed configuration')

        return Configuration(config.get('email'), config.get('password'))

    @staticmethod
    def create(email, password):
        if os.path.exists(Configuration.get_config_path()):
            os.unlink(Configuration.get_config_path())

        with open(Configuration.get_config_path(), 'w+') as f:
            yaml.safe_dump({
                'email': email,
                'password': password
            }, f)

        return Configuration.load()
