import hashlib
import os.path

import httpx
from librespot.core import Session

from spoffline.cacher import Cacher
from spoffline.configuration import config
from spoffline.helpers.exceptions import SpotifyException


class Spotify:
    def __init__(self):
        self.cache = Cacher('spotify.api')
        self._user_session = None
        os.makedirs(os.path.dirname(self.credentials_cache_path), exist_ok=True)

    @property
    def md5credentials(self):
        hash_credentials = hashlib.md5()
        hash_credentials.update(f'{config.credentials.email}:{config.credentials.password}'.encode())
        return hash_credentials.hexdigest()

    @property
    def credentials_cache_path(self):
        return os.path.join(
            config.paths.cache,
            'spotify',
            'credentials.json'
        )

    def get_api_token(self):
        token = self.cache.get('api:token')
        if token:
            return token

        with httpx.Client() as client:
            req = client.post(
                'https://accounts.spotify.com/api/token',
                data={
                    'grant_type': 'client_credentials',
                    'client_id': config.credentials.client_id,
                    'client_secret': config.credentials.client_secret
                }
            )

        if req.status_code != httpx.codes.OK:
            raise SpotifyException('Unable to fetch token')

        self.cache.set('api:token', req.json().get('access_token'), req.json().get('expires_in') - 600)

        return req.json().get('access_token')

    def get_api_session(self):
        return httpx.Client(
            headers={
                'Authorization': f'Bearer {self.get_api_token()}'
            }
        )

    def get_user_session(self):
        if self._user_session and self._user_session.is_valid():
            return self._user_session

        if os.path.exists(self.credentials_cache_path):
            last_credentials = self.cache.get('credentials:hash') or ''

            if last_credentials == self.md5credentials:
                self._user_session = Session.Builder(Session.Configuration(
                    stored_credentials_file=self.credentials_cache_path,
                    store_credentials=True,
                    cache_enabled=True,
                    cache_dir=os.path.dirname(self.credentials_cache_path),
                    do_cache_clean_up=True,
                    retry_on_chunk_error=True,
                )).stored_file(self.credentials_cache_path).create()
                if self._user_session.is_valid():
                    return self._user_session
            else:
                os.unlink(self.credentials_cache_path)

        self._user_session = Session.Builder(Session.Configuration(
            stored_credentials_file=self.credentials_cache_path,
            store_credentials=True,
            cache_enabled=True,
            cache_dir=os.path.dirname(self.credentials_cache_path),
            do_cache_clean_up=True,
            retry_on_chunk_error=True,
        )).user_pass(
            config.credentials.email,
            config.credentials.password
        ).create()

        self.cache.set('credentials:hash', self.md5credentials)

        return self._user_session
