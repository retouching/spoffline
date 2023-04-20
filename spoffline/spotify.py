import hashlib
import math
import os.path
import time
from contextlib import contextmanager

import httpx
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.core import Session
from librespot.metadata import TrackId

from spoffline.cacher import Cacher
from spoffline.configuration import config
from spoffline.helpers.exceptions import SpotifyException
from spoffline.models.song import Song


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

    def get_track_infos(self, track_id):
        song = self.cache.get(f'song:infos:{track_id}')
        if song:
            return song

        with self.get_api_session() as client:
            req = client.get(
                f'https://api.spotify.com/v1/tracks/{track_id}',
            )

        if req.status_code != httpx.codes.OK:
            raise SpotifyException(f'Unable to fetch track info (HTTP code: {req.status_code})')

        data = req.json()

        image = next(iter(sorted(
            data.get('album').get('images'),
            key=lambda i: i.get('height'),
            reverse=True
        ))).get('url')

        song = Song(
            id=data.get('id'),
            name=data.get('name'),
            artists=[a.get('name') for a in data.get('artists')],
            album=data.get('album').get('name'),
            cover_url=image
        )

        self.cache.set(f'song:infos:{track_id}', song, 60 * 60 * 24 * 7)

        return song

    def get_album_tracks(self, album_id):
        songs = self.cache.get(f'album:{album_id}')
        if songs:
            for song in songs:
                yield song
            return

        songs = []

        with self.get_api_session() as client:
            req = client.get(f'https://api.spotify.com/v1/albums/{album_id}')

        if req.status_code != httpx.codes.OK:
            raise SpotifyException(f'Unable to fetch album info (HTTP code: {req.status_code})')

        data = req.json()

        image = next(iter(sorted(
            data.get('images'),
            key=lambda i: i.get('height'),
            reverse=True
        ))).get('url')

        max_pages = int(math.ceil(data.get('total_tracks') / float(50))) or 1

        with self.get_api_session() as client:
            for page in range(1, max_pages + 1):
                req = client.get(
                    f'https://api.spotify.com/v1/albums/{album_id}/tracks',
                    params={
                        'limit': 50,
                        'offset': (page - 1) * 50
                    }
                )

                if req.status_code != httpx.codes.OK:
                    raise SpotifyException(f'Unable to fetch album tracks (HTTP code: {req.status_code})')

                songs_data = req.json().get('items')

                for song_data in songs_data:
                    song = Song(
                        id=song_data.get('id'),
                        name=song_data.get('name'),
                        artists=[a.get('name') for a in song_data.get('artists')],
                        album=data.get('name'),
                        cover_url=image
                    )

                    self.cache.set(f'song:infos:{song.id}', song, 60 * 60 * 24 * 7)
                    songs.append(song)

                    yield song

                if page != max_pages:
                    time.sleep(5)

        self.cache.set(f'album:{album_id}', songs, 60 * 60 * 24 * 7)

    def get_playlist_tracks(self, playlist_id):
        songs = self.cache.get(f'playlist:{playlist_id}')
        if songs:
            for song in songs:
                yield song
            return

        songs = []
        next_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset=0&limit=100'

        with self.get_api_session() as client:
            while next_url is not None:
                req = client.get(next_url)

                if req.status_code != httpx.codes.OK:
                    raise SpotifyException(f'Unable to fetch playlist tracks (HTTP code: {req.status_code})')

                data = req.json()

                songs_data = data.get('items')
                next_url = data.get('next')

                for song_data in songs_data:
                    if song_data.get('track').get('type') != 'track' or song_data.get('is_local'):
                        continue

                    song = Song(
                        id=song_data.get('track').get('id'),
                        name=song_data.get('track').get('name'),
                        artists=[a.get('name') for a in song_data.get('track').get('artists')],
                        album=song_data.get('track').get('album').get('name'),
                        cover_url=next(iter(sorted(
                            song_data.get('track').get('album').get('images'),
                            key=lambda i: i.get('height'),
                            reverse=True
                        ))).get('url')
                    )

                    self.cache.set(f'song:infos:{song.id}', song, 60 * 60 * 24 * 7)
                    songs.append(song)

                    yield song

                if next_url:
                    time.sleep(5)

        self.cache.set(f'playlist:{playlist_id}', songs, 60 * 60 * 24 * 7)

    @contextmanager
    def get_track_content(self, track_id):
        playable_id = self.cache.get(f'song:playable:{track_id}')
        if not playable_id:
            playable_id = TrackId.from_uri(f'spotify:track:{track_id}')
            self.cache.set(f'song:playable:{track_id}', playable_id)

        stream = self.get_user_session().content_feeder().load(
            TrackId.from_uri(f'spotify:track:{track_id}'),
            VorbisOnlyAudioQuality(
                # TODO: Autodetect if account is premium or not
                AudioQuality.VERY_HIGH if config.credentials.is_premium else AudioQuality.HIGH
            ),
            False,
            None
        ).input_stream.stream()

        try:
            yield stream
        finally:
            stream.close()
