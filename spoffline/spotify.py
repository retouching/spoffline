import hashlib
import os.path
import re
import time
from urllib.parse import urlparse
from urllib.parse import parse_qs

import httpx
from librespot.core import Session

from spoffline.cacher import Cacher
from spoffline.configuration import config
from spoffline.helpers.exceptions import SpotifyException


class Spotify:
    KEEP_IN_CACHE = 60 * 60 * 12
    BASE_URL = 'https://api.spotify.com/v1/'

    def __init__(self):
        self.cache = Cacher('spotify.api')
        self._user_session = None
        os.makedirs(os.path.dirname(self.credentials_cache_path), exist_ok=True)

    @staticmethod
    def parse_url(url):
        match = re.match(
            r'https?://open\.spotify\.com/(album|artist|episode|playlist|track|show)/([^?]+)',
            url
        )

        if not match:
            raise SpotifyException('Invalid URL provided')

        return {f'{match.group(1)}_id': match.group(2)}

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

    def set_cache(self, key, data):
        return self.cache.set(key, data, Spotify.KEEP_IN_CACHE)

    def get_global_api_token(self):
        token = self.cache.get('api:token:global')
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

    def get_user_api_token(self):
        return self.get_user_session().tokens().get_token(
            'playlist-read-private',
            'user-read-private',
            'user-read-email'
        ).access_token

    def get_api_session(self, read_playlist=False):
        session = httpx.Client(base_url=Spotify.BASE_URL)

        user_data = self.cache.get(f'user:{self.md5credentials}')
        if not user_data or read_playlist:
            session.headers = {
                'Authorization': f'Bearer {self.get_user_api_token()}'
            }

            if not user_data:
                with httpx.Client(base_url=Spotify.BASE_URL, headers=session.headers) as client:
                    req = client.get('/me')

                if req.status_code != httpx.codes.OK:
                    raise SpotifyException('Unable to fetch current user')

                user_data = req.json()
                self.set_cache(f'user:{self.md5credentials}', user_data)
        else:
            session.headers = {
                'Authorization': f'Bearer {self.get_global_api_token()}'
            }

        session.params = {'market': user_data.get('country')}

        return session

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

    def get_track(self, track_id, from_cache=True):
        if type(track_id) != str or len(track_id) < 1:
            raise SpotifyException('Invalid track id')

        if from_cache:
            track_or_exc = self.cache.get(f'track:{track_id}')

            if track_or_exc:
                if type(track_or_exc) == SpotifyException:
                    raise track_or_exc
                return track_or_exc

        with self.get_api_session() as session:
            req = session.get(f'/tracks/{track_id}')

        if req.status_code != httpx.codes.OK:
            exc = SpotifyException(
                'Track not found' if req.status_code in [
                    httpx.codes.BAD_REQUEST,
                    httpx.codes.NOT_FOUND
                ] else 'Unable to fetch track'
            )

            if req.status_code in [
                httpx.codes.BAD_REQUEST,
                httpx.codes.NOT_FOUND
            ]:
                self.set_cache(f'track:{track_id}', exc)

            raise exc

        data = req.json()

        image = next(iter(sorted(
            data.get('album').get('images'),
            key=lambda i: i.get('height') or 0,
            reverse=True
        )), None)

        track = {
            'id': data.get('id'),
            'name': data.get('name'),
            'album': {
                'id': data.get('album').get('id'),
                'name': data.get('album').get('name'),
                'cover': image.get('url') if image else None,
                'tracks': data.get('album').get('total_tracks')
            },
            'number': data.get('track_number') or 1,
            'artists': [{
                'id': a.get('id'),
                'name': a.get('name')
            } for a in data.get('artists')]
        }

        self.set_cache(f'track:{track_id}', track)

        return track

    def get_album(self, album_id, from_cache=True):
        if type(album_id) != str or len(album_id) < 1:
            raise SpotifyException('Invalid album id')

        if from_cache:
            album_or_exc = self.cache.get(f'album:{album_id}')

            if album_or_exc:
                if type(album_or_exc) == SpotifyException:
                    raise album_or_exc
                return album_or_exc

        with self.get_api_session() as session:
            req = session.get(f'/albums/{album_id}')

        if req.status_code != httpx.codes.OK:
            exc = SpotifyException(
                'Album not found' if req.status_code in [
                    httpx.codes.BAD_REQUEST,
                    httpx.codes.NOT_FOUND
                ] else 'Unable to fetch album'
            )

            if req.status_code in [
                httpx.codes.BAD_REQUEST,
                httpx.codes.NOT_FOUND
            ]:
                self.set_cache(f'album:{album_id}', exc)
                self.set_cache(f'album:{album_id}:tracks', exc)

            raise exc

        data = req.json()

        image = next(iter(sorted(
            data.get('images'),
            key=lambda i: i.get('height') or 0,
            reverse=True
        )), None)

        album = {
            'id': data.get('id'),
            'name': data.get('name'),
            'cover': image.get('url') if image else None,
            'tracks': data.get('total_tracks')
        }

        self.set_cache(f'album:{album_id}', album)

        return album

    def get_album_tracks(self, album_id, from_cache=True):
        if type(album_id) != str or len(album_id) < 1:
            raise SpotifyException('Invalid album id')

        if from_cache:
            tracks_or_exc = self.cache.get(f'album:{album_id}:tracks')

            if tracks_or_exc:
                if type(tracks_or_exc) == SpotifyException:
                    raise tracks_or_exc

                for track in tracks_or_exc:
                    yield track

                return

            album_or_exc = self.cache.get(f'album:{album_id}')
            if album_or_exc and type(album_or_exc) == SpotifyException:
                raise album_or_exc

        album = self.get_album(album_id, from_cache)
        tracks = []
        next_url = f'/albums/{album_id}/tracks?offset=0&limit=50'

        if from_cache:
            saved_chunk = self.cache.get(f'album:{album_id}:tracks_chunk')
            if saved_chunk:
                tracks = saved_chunk.get('tracks')
                next_url = saved_chunk.get('next_url')

                for track in tracks:
                    yield track

        while next_url is not None:
            with self.get_api_session() as session:
                req = session.get(next_url)

            if req.status_code != httpx.codes.OK:
                raise SpotifyException('Unable to fetch album tracks')

            data = req.json()
            next_url = None

            if data.get('next'):
                parsed_next_url = parse_qs(urlparse(data.get('next')).query)
                next_url = f'/albums/{album_id}' \
                           f'/tracks' \
                           f'?offset={parsed_next_url.get("offset")[0]}' \
                           f'&limit={parsed_next_url.get("limit")[0]}'

            for item in data.get('items'):
                if next(filter(
                    lambda t: t.get('id') == item.get('id'),
                    tracks
                ), None):
                    continue

                track = {
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'album': album,
                    'number': item.get('track_number') or 1,
                    'artists': [{
                        'id': a.get('id'),
                        'name': a.get('name')
                    } for a in item.get('artists')]
                }

                self.set_cache(f'tracks:{track.get("id")}', track)
                tracks.append(track)

                yield track

            self.set_cache(f'album:{album_id}:tracks_chunk', {
                'tracks': tracks,
                'next_url': next_url
            })

            if next_url:
                time.sleep(2)

    def get_artist(self, artist_id, from_cache=True):
        if type(artist_id) != str or len(artist_id) < 1:
            raise SpotifyException('Invalid artist id')

        if from_cache:
            artist_or_exc = self.cache.get(f'artist:{artist_id}')

            if artist_or_exc:
                if type(artist_or_exc) == SpotifyException:
                    raise artist_or_exc
                return artist_or_exc

        with self.get_api_session() as session:
            req = session.get(f'/artists/{artist_id}')

        if req.status_code != httpx.codes.OK:
            exc = SpotifyException(
                'Artist not found' if req.status_code in [
                    httpx.codes.BAD_REQUEST,
                    httpx.codes.NOT_FOUND
                ] else 'Unable to fetch artist'
            )

            if req.status_code in [
                httpx.codes.BAD_REQUEST,
                httpx.codes.NOT_FOUND
            ]:
                self.set_cache(f'artist:{artist_id}', exc)

            raise exc

        data = req.json()

        artist = {
            'id': data.get('id'),
            'name': data.get('name')
        }

        self.set_cache(f'artist:{artist_id}', artist)

        return artist

    def get_artist_albums(self, artist_id, from_cache=True):
        if type(artist_id) != str or len(artist_id) < 1:
            raise SpotifyException('Invalid artist id')

        if from_cache:
            artist_albums_or_exc = self.cache.get(f'artist:{artist_id}')

            if artist_albums_or_exc:
                if type(artist_albums_or_exc) == SpotifyException:
                    raise artist_albums_or_exc

                for album in artist_albums_or_exc:
                    yield album

                return

            artist_or_exc = self.cache.get(f'album:{artist_id}')
            if artist_or_exc and type(artist_or_exc) == SpotifyException:
                raise artist_or_exc

        albums = []
        next_url = f'/artists/{artist_id}/albums?offset=0&limit=50'

        if from_cache:
            saved_chunk = self.cache.get(f'artist:{artist_id}:albums_chunk')
            if saved_chunk:
                albums = saved_chunk.get('albums')
                next_url = saved_chunk.get('next_url')

                for album in albums:
                    yield album

        while next_url is not None:
            with self.get_api_session() as session:
                req = session.get(next_url)

            if req.status_code != httpx.codes.OK:
                raise SpotifyException('Unable to fetch artist albums')

            data = req.json()
            next_url = None

            if data.get('next'):
                parsed_next_url = parse_qs(urlparse(data.get('next')).query)
                next_url = f'/artists/{artist_id}' \
                           f'/albums' \
                           f'?offset={parsed_next_url.get("offset")[0]}' \
                           f'&limit={parsed_next_url.get("limit")[0]}'

            for item in data.get('items'):
                if next(filter(
                    lambda a: a.get('id') == item.get('id'),
                    albums
                ), None):
                    continue

                image = next(iter(sorted(
                    item.get('images'),
                    key=lambda i: i.get('height') or 0,
                    reverse=True
                )), None)

                album = {
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'cover': image.get('url') if image else None,
                    'tracks': item.get('total_tracks')
                }

                self.set_cache(f'album:{album.get("id")}', album)
                albums.append(album)

                yield album

            self.set_cache(f'artist:{artist_id}:albums_chunk', {
                'albums': albums,
                'next_url': next_url
            })

            if next_url:
                time.sleep(2)
