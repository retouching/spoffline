import os

import httpx
from librespot.core import Session as LibrespotSession

from spoffline.constants import SPOTIFY_BASEURL
from spoffline.helpers.exceptions import SpotifyException
from spoffline.spotify.managers.manager import Manager
from spoffline.models.credentials import Credentials
from spoffline.models.userdata import UserData


class Session(Manager):
    def __init__(self, client):
        super().__init__(client)
        self._session = None

    @property
    def credentials(self):
        return Credentials(email=self.client.email, password=self.client.password)

    @property
    def user(self):
        current = self.from_cache(f'user:{self.credentials.hashed}', False)

        if not current:
            with httpx.Client(
                base_url=SPOTIFY_BASEURL,
                headers={
                    'Authorization': f'Bearer {self.access_token}'
                }
            ) as client:
                req = client.get('/me')

                if req.status_code != httpx.codes.OK:
                    raise SpotifyException('Unable to fetch current user')

                current = UserData(**req.json())

                self.set_cache(f'user:{self.credentials.hashed}', current, False)

        return current

    @property
    def session(self):
        if self._session and self._session.is_valid():
            return self._session

        credentials_path = os.path.join(
            self.client.cache_path,
            'spotify',
            'credentials.json'
        )

        if os.path.exists(credentials_path):
            last_credentials = self.from_cache('credentials', False)

            if last_credentials and last_credentials == self.credentials.hashed:
                self._session = LibrespotSession.Builder(LibrespotSession.Configuration(
                    stored_credentials_file=credentials_path,
                    store_credentials=True,
                    cache_enabled=True,
                    cache_dir=os.path.dirname(credentials_path),
                    do_cache_clean_up=True,
                    retry_on_chunk_error=True,
                )).stored_file(credentials_path).create()
                if self._session.is_valid():
                    return self._session
            else:
                os.unlink(credentials_path)

        self._session = LibrespotSession.Builder(LibrespotSession.Configuration(
            stored_credentials_file=credentials_path,
            store_credentials=True,
            cache_enabled=True,
            cache_dir=os.path.dirname(credentials_path),
            do_cache_clean_up=True,
            retry_on_chunk_error=True,
        )).user_pass(self.credentials.email, self.credentials.password).create()

        self.set_cache('credentials', self.credentials, False)

        return self._session

    @property
    def access_token(self):
        return self.session.tokens().get_token(
            'playlist-read-private',
            'user-read-private',
            'user-read-email'
        ).access_token

    def get_api_session(self):
        session = httpx.Client(
            base_url=SPOTIFY_BASEURL,
            params={'market': self.user.country},
            headers={
                'Authorization': f'Bearer {self.access_token}'
            }
        )

        return session
