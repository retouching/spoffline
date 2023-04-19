import json
import os
import pickle
import re
import time

from spoffline.configuration import config


class Cacher:
    def __init__(self, name):
        self.name = name

        if not re.match(r'^[0-9A-Za-z-_.]+$', name):
            raise ValueError('Invalid cacher name')

        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w+') as f:
                f.write('{}')

    @property
    def path(self):
        final_path = [config.paths.cache]
        name_splited = [n for n in self.name.split('.') if n and len(n) > 0]

        for index, n in enumerate(name_splited):
            final_path.append(f'{n}{".json" if len(name_splited) == index + 1 else ""}')

        return os.path.join(*final_path)

    def get(self, key=None):
        with open(self.path, 'r') as f:
            data = json.load(f)
        if not key:
            return data
        if not data.get(key):
            return None
        if data.get(key).get('timeout') and data.get(key).get('timeout') < time.time():
            return None
        return pickle.loads(bytes.fromhex(data.get(key).get('data')))

    def set(self, key, data, timeout=None):
        data = {**self.get(), key: {'data': pickle.dumps(data).hex(), 'timeout': int(time.time()) + timeout}}
        with open(self.path, 'w') as f:
            json.dump(data, f, indent=4)
