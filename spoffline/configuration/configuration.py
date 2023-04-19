import os
import yaml

from pydantic import BaseModel

from spoffline.helpers import project_path
from spoffline.configuration.paths import PathsConfiguration


class Configuration(BaseModel):
    paths: PathsConfiguration = PathsConfiguration()

    @staticmethod
    def load():
        config_path = os.path.join(project_path, 'config.yml')
        config_exist = os.path.exists(config_path)

        with open(config_path, 'r' if config_exist else 'w+') as f:
            data = f.read() if config_exist else ''

            if not config_exist:
                f.write(data)

        return Configuration(**(yaml.safe_load(data) or {}))
