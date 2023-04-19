import os

from pydantic import BaseModel

from spoffline.helpers import project_path


class PathsConfiguration(BaseModel):
    cache: str = os.path.join(project_path, 'cache')
    binaries: str = os.path.join(project_path, 'binaries')
    downloads: str = os.path.join(project_path, 'downloads')
    temp: str = os.path.join(project_path, 'temp')

    def __init__(self, **data):
        super().__init__(**data)

        for path in [
            self.cache,
            self.binaries,
            self.downloads,
            self.temp
        ]:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
