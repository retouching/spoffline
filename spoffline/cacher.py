import json
import os
import pickle
import re
import time


class Cacher:
    def __init__(self, name, cache_path):
        self.name = name
        self.cache_path = cache_path
        self.data = None

        if not re.match(r'^[0-9A-Za-z-_.]+$', name):
            raise ValueError('Invalid cacher name')

        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w+') as f:
                f.write('{}')
            self.data = {}
        else:
            with open(self.path, 'r') as f:
                self.data = json.load(f)

    @property
    def path(self):
        final_path = [self.cache_path]
        name_splited = [n for n in self.name.split('.') if n and len(n) > 0]

        for index, n in enumerate(name_splited):
            final_path.append(f'{n}{".json" if len(name_splited) == index + 1 else ""}')

        return os.path.join(*final_path)

    def get(self, key):
        if not self.data.get(key):
            return None
        if self.data.get(key).get('timeout') and self.data.get(key).get('timeout') < time.time():
            return None
        return pickle.loads(bytes.fromhex(self.data.get(key).get('data')))

    def set(self, key, data, timeout=None):
        self.data = {
            **self.data,
            key: {
                'data': pickle.dumps(data).hex(),
                'timeout': int(time.time()) + timeout if timeout else None
            }
        }

        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=4)

    def values(self, prefix=None):
        for key in self.data:
            if prefix and not key.startswith(prefix):
                continue

            if self.data.get(key).get('timeout') and self.data.get(key).get('timeout') < time.time():
                continue

            yield self.data.get(key)
