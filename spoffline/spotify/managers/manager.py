import abc

from spoffline.cacher import Cacher


class Manager(abc.ABC):
    KEEP_IN_CACHE = 60 * 60 * 12

    def __init__(self, client):
        self.client = client
        self.cache = Cacher(
            f'spotify.{self.__class__.__name__.lower()}',
            self.client.cache_path
        )

    def get(self, _id, from_cache=True):
        raise NotImplementedError

    def to_model(self, data):
        raise NotImplementedError

    def set_cache(self, key, data, by_country=True):
        country = 'GLOBAL' if not by_country else self.client.session.user.country

        return self.cache.set(
            f'{key}:{country}',
            data,
            Manager.KEEP_IN_CACHE
        )

    def from_cache(self, key, by_country=True):
        country = 'GLOBAL' if not by_country else self.client.session.user.country
        data = self.cache.get(f'{key}:{country}')
        return data
