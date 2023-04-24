import hashlib
import os.path
import re
import time
from contextlib import contextmanager
from urllib.parse import urlparse
from urllib.parse import parse_qs

import httpx
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.core import Session
from librespot.metadata import EpisodeId, TrackId

from spoffline.cacher import Cacher
from spoffline.configuration import config
from spoffline.helpers.exceptions import SpotifyException


class Spotify:
    KEEP_IN_CACHE = 60 * 60 * 12
    BASE_URL = 'https://api.spotify.com/v1/'

    def __init__(self):
        self.cache = Cacher('spotify.data')
        self._user_session = None
        os.makedirs(os.path.dirname(self.credentials_cache_path), exist_ok=True)

        # Init user session
        self.get_user_session()

    @staticmethod
    def parse_url(url):
        match = re.match(
            r'https?://open\.spotify\.com/(album|artist|episode|playlist|track|show)/([^?]+)',
            url
        )

        if not match:
            raise SpotifyException('Invalid URL provided')

        return match.group(2), match.group(1)

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

    def set_cache(self, key, data, by_country=True):
        country = ''

        if by_country:
            country += f':{self.user_data.get("country")}'

        return self.cache.set(
            f'{key}{country}',
            data,
            Spotify.KEEP_IN_CACHE
        )

    def get_cache(self, key, by_country=True):
        country = ''

        if by_country:
            country += f':{self.user_data.get("country")}'

        return self.cache.get(f'{key}{country}')

    @property
    def user_data(self):
        user_data = self.get_cache(f'user:{self.md5credentials}', False)

        if not user_data:
            with httpx.Client(
                base_url=Spotify.BASE_URL,
                headers={
                    'Authorization': f'Bearer {self.get_user_api_token()}'
                }
            ) as client:
                req = client.get('/me')

                if req.status_code != httpx.codes.OK:
                    raise SpotifyException('Unable to fetch current user')

                user_data = req.json()
                self.set_cache(f'user:{self.md5credentials}', user_data, False)

        return user_data

    @property
    def user_quality(self):
        return AudioQuality.VERY_HIGH if self.user_data.get('product') == 'premium' else AudioQuality.HIGH

    def get_global_api_token(self):
        token = self.get_cache('api:token', False)
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
        session = httpx.Client(
            base_url=Spotify.BASE_URL,
            params={'market': self.user_data.get('country')},
            headers={
                'Authorization': f'Bearer {self.get_user_api_token() if read_playlist else self.get_global_api_token()}'
            }
        )

        return session

    def get_user_session(self):
        if self._user_session and self._user_session.is_valid():
            return self._user_session

        if os.path.exists(self.credentials_cache_path):
            last_credentials = self.get_cache('credentials:hash', False) or ''

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

        self.set_cache('credentials:hash', self.md5credentials, False)

        return self._user_session

    def get_track(self, track_id, from_cache=True):
        if type(track_id) != str or len(track_id) < 1:
            raise SpotifyException('Invalid track id')

        if from_cache:
            track_or_exc = self.get_cache(f'track:{track_id}')

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

        if not data.get('is_playable', True):
            raise SpotifyException('This track is not available in your country')

        image = next(iter(sorted(
            data.get('album').get('images'),
            key=lambda i: i.get('height') or 0,
            reverse=True
        )), None)

        album = {
                'id': data.get('album').get('id'),
                'name': data.get('album').get('name'),
                'cover': image.get('url') if image else None,
                'tracks': data.get('album').get('total_tracks')
            }
        artists = [{
                'id': a.get('id'),
                'name': a.get('name')
            } for a in data.get('artists')]

        for a in artists:
            self.set_cache(f'artist:{a.get("id")}', a)
        self.set_cache(f'album:{album.get("id")}', album)

        track = {
            'id': data.get('id'),
            'name': data.get('name'),
            'album': album,
            'number': data.get('track_number') or 1,
            'artists': artists,
            'disc': data.get('disc_number') or 1
        }

        self.set_cache(f'track:{track_id}', track)

        return track

    def get_album(self, album_id, from_cache=True):
        if type(album_id) != str or len(album_id) < 1:
            raise SpotifyException('Invalid album id')

        if from_cache:
            album_or_exc = self.get_cache(f'album:{album_id}')

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
            tracks_or_exc = self.get_cache(f'album:{album_id}:tracks')

            if tracks_or_exc:
                if type(tracks_or_exc) == SpotifyException:
                    raise tracks_or_exc

                for track in tracks_or_exc:
                    yield track

                return

            album_or_exc = self.get_cache(f'album:{album_id}')
            if album_or_exc and type(album_or_exc) == SpotifyException:
                raise album_or_exc

        album = self.get_album(album_id, from_cache)
        tracks = []
        next_url = f'/albums/{album_id}/tracks?offset=0&limit=50'

        if from_cache:
            saved_chunk = self.get_cache(f'album:{album_id}:tracks_chunk')
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
                           f'?offset={parsed_next_url.get(b"offset")[0]}' \
                           f'&limit={parsed_next_url.get(b"limit")[0]}'

            for item in data.get('items'):
                if next(filter(
                    lambda t: t.get('id') == item.get('id'),
                    tracks
                ), None):
                    continue

                if not item.get('is_playable', True):
                    continue

                artists = [{
                    'id': a.get('id'),
                    'name': a.get('name')
                } for a in item.get('artists')]

                for a in artists:
                    self.set_cache(f'artist:{a.get("id")}', a)

                track = {
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'album': album,
                    'number': item.get('track_number') or 1,
                    'artists': artists,
                    'disc': item.get('disc_number') or 1
                }

                self.set_cache(f'track:{track.get("id")}', track)
                tracks.append(track)

                yield track

            self.set_cache(f'album:{album_id}:tracks_chunk', {
                'tracks': tracks,
                'next_url': next_url
            })

            if next_url:
                time.sleep(2)

        self.set_cache(f'album:{album_id}:tracks', tracks)

    def get_artist(self, artist_id, from_cache=True):
        if type(artist_id) != str or len(artist_id) < 1:
            raise SpotifyException('Invalid artist id')

        if from_cache:
            artist_or_exc = self.get_cache(f'artist:{artist_id}')

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
            artist_albums_or_exc = self.get_cache(f'artist:{artist_id}:albums')

            if artist_albums_or_exc:
                if type(artist_albums_or_exc) == SpotifyException:
                    raise artist_albums_or_exc

                for album in artist_albums_or_exc:
                    yield album

                return

            artist_or_exc = self.get_cache(f'album:{artist_id}')
            if artist_or_exc and type(artist_or_exc) == SpotifyException:
                raise artist_or_exc

        albums = []
        next_url = f'/artists/{artist_id}/albums?offset=0&limit=50'

        if from_cache:
            saved_chunk = self.get_cache(f'artist:{artist_id}:albums_chunk')
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
                           f'?offset={parsed_next_url.get(b"offset")[0]}' \
                           f'&limit={parsed_next_url.get(b"limit")[0]}'

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

        self.set_cache(f'artist:{artist_id}:albums', albums)

    def get_episode(self, episode_id, from_cache=True):
        if type(episode_id) != str or len(episode_id) < 1:
            raise SpotifyException('Invalid episode id')

        if from_cache:
            episode_or_exc = self.get_cache(f'episode:{episode_id}')

            if episode_or_exc:
                if type(episode_or_exc) == SpotifyException:
                    raise episode_or_exc
                return episode_or_exc

        with self.get_api_session() as session:
            req = session.get(f'/episodes/{episode_id}')

        if req.status_code != httpx.codes.OK:
            exc = SpotifyException(
                'Episode not found' if req.status_code in [
                    httpx.codes.BAD_REQUEST,
                    httpx.codes.NOT_FOUND
                ] else 'Unable to fetch episode'
            )

            if req.status_code in [
                httpx.codes.BAD_REQUEST,
                httpx.codes.NOT_FOUND
            ]:
                self.set_cache(f'episode:{episode_id}', exc)

            raise exc

        data = req.json()

        if not data.get('is_playable', True):
            raise SpotifyException('This episode is not available in your country')

        image = next(iter(sorted(
            data.get('show').get('images'),
            key=lambda i: i.get('height') or 0,
            reverse=True
        )), None)

        show = {
                'id': data.get('show').get('id'),
                'name': data.get('show').get('name'),
                'cover': image.get('url') if image else None,
                'episodes': data.get('show').get('total_episodes')
            }

        self.set_cache(f'show:{show.get("id")}', show)

        episode = {
            'id': data.get('id'),
            'name': data.get('name'),
            'show': show
        }

        self.set_cache(f'episode:{episode_id}', episode)

        return episode

    def get_show(self, show_id, from_cache=True):
        if type(show_id) != str or len(show_id) < 1:
            raise SpotifyException('Invalid show id')

        if from_cache:
            show_or_exc = self.get_cache(f'show:{show_id}')

            if show_or_exc:
                if type(show_or_exc) == SpotifyException:
                    raise show_or_exc
                return show_or_exc

        with self.get_api_session() as session:
            req = session.get(f'/shows/{show_id}')

        if req.status_code != httpx.codes.OK:
            exc = SpotifyException(
                'Show not found' if req.status_code in [
                    httpx.codes.BAD_REQUEST,
                    httpx.codes.NOT_FOUND
                ] else 'Unable to fetch show'
            )

            if req.status_code in [
                httpx.codes.BAD_REQUEST,
                httpx.codes.NOT_FOUND
            ]:
                self.set_cache(f'show:{show_id}', exc)
                self.set_cache(f'show:{show_id}:episodes', exc)

            raise exc

        data = req.json()

        image = next(iter(sorted(
            data.get('images'),
            key=lambda i: i.get('height') or 0,
            reverse=True
        )), None)

        show = {
            'id': data.get('id'),
            'name': data.get('name'),
            'cover': image.get('url') if image else None,
            'tracks': data.get('total_episodes')
        }

        self.set_cache(f'show:{show_id}', show)

        return show

    def get_show_episodes(self, show_id, from_cache=True):
        if type(show_id) != str or len(show_id) < 1:
            raise SpotifyException('Invalid show id')

        if from_cache:
            episodes_or_exc = self.get_cache(f'show:{show_id}:episodes')

            if episodes_or_exc:
                if type(episodes_or_exc) == SpotifyException:
                    raise episodes_or_exc

                for episode in episodes_or_exc:
                    yield episode

                return

            show_or_exc = self.get_cache(f'show:{show_id}')
            if show_or_exc and type(show_or_exc) == SpotifyException:
                raise show_or_exc

        show = self.get_show(show_id, from_cache)
        episodes = []
        next_url = f'/shows/{show_id}/episodes?offset=0&limit=50'

        if from_cache:
            saved_chunk = self.get_cache(f'show:{show_id}:episodes_chunk')
            if saved_chunk:
                episodes = saved_chunk.get('episodes')
                next_url = saved_chunk.get('next_url')

                for episode in episodes:
                    yield episode

        while next_url is not None:
            with self.get_api_session() as session:
                req = session.get(next_url)

            if req.status_code != httpx.codes.OK:
                raise SpotifyException('Unable to fetch show episodes')

            data = req.json()
            next_url = None

            if data.get('next'):
                parsed_next_url = parse_qs(urlparse(data.get('next')).query)
                next_url = f'/shows/{show_id}' \
                           f'/episodes' \
                           f'?offset={parsed_next_url.get(b"offset")[0]}' \
                           f'&limit={parsed_next_url.get(b"limit")[0]}'

            episodes_parsed = []

            for item in data.get('items'):
                if next(filter(
                    lambda e: e.get('id') == item.get('id'),
                    episodes
                ), None):
                    continue

                if not item.get('is_playable', True):
                    continue

                episode = {
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'show': show
                }

                self.set_cache(f'episode:{episode.get("id")}', episode)
                episodes.append(episode)
                episodes_parsed.append(episode)

            self.set_cache(f'show:{show_id}:episodes_chunk', {
                'episodes': episodes,
                'next_url': next_url
            })

            for episode_parsed in episodes_parsed:
                yield episode_parsed

            if next_url:
                time.sleep(2)

        self.set_cache(f'show:{show_id}:episodes', episodes)

    def get_playlist(self, playlist_id, from_cache=True, with_account=False):
        if type(playlist_id) != str or len(playlist_id) < 1:
            raise SpotifyException('Invalid playlist id')

        if from_cache:
            playlist_or_exc = self.get_cache(f'playlist:{playlist_id}:{self.md5credentials}')

            if playlist_or_exc:
                if type(playlist_or_exc) == SpotifyException:
                    raise playlist_or_exc
                return playlist_or_exc

        with self.get_api_session(with_account) as session:
            req = session.get(f'/playlists/{playlist_id}')

        if req.status_code != httpx.codes.OK:
            exc = SpotifyException(
                'Playlist not found' if req.status_code in [
                    httpx.codes.BAD_REQUEST,
                    httpx.codes.NOT_FOUND
                ] else 'Unable to fetch playlist'
            )

            if req.status_code in [
                httpx.codes.BAD_REQUEST,
                httpx.codes.NOT_FOUND
            ]:
                self.set_cache(f'playlist:{playlist_id}:{self.md5credentials}', exc)
                self.set_cache(f'playlist:{playlist_id}:{self.md5credentials}:items', exc)

            raise exc

        data = req.json()

        image = next(iter(sorted(
            data.get('images'),
            key=lambda i: i.get('height') or 0,
            reverse=True
        )), None)

        playlist = {
            'id': data.get('id'),
            'name': data.get('name'),
            'cover': image.get('url') if image else None,
            'tracks': data.get('tracks').get('total')
        }

        self.set_cache(f'playlist:{playlist_id}:{self.md5credentials}', playlist)

        return playlist

    def get_playlist_items(self, playlist_id, from_cache=True, with_account=False):
        if type(playlist_id) != str or len(playlist_id) < 1:
            raise SpotifyException('Invalid playlist id')

        if from_cache:
            items_or_exc = self.get_cache(f'playlist:{playlist_id}:{self.md5credentials}:items')

            if items_or_exc:
                if type(items_or_exc) == SpotifyException:
                    raise items_or_exc

                for item in items_or_exc:
                    yield item

                return

            playlist_or_exc = self.get_cache(f'playlist:{playlist_id}:{self.md5credentials}')
            if playlist_or_exc and type(playlist_or_exc) == SpotifyException:
                raise playlist_or_exc

        items = []
        next_url = f'/playlists/{playlist_id}/tracks?offset=0&limit=50'

        if from_cache:
            saved_chunk = self.get_cache(f'playlist:{playlist_id}:{self.md5credentials}:items_chunk')
            if saved_chunk:
                items = saved_chunk.get('items')
                next_url = saved_chunk.get('next_url')

                for item in items:
                    yield item

        while next_url is not None:
            with self.get_api_session(with_account) as session:
                req = session.get(next_url)

            if req.status_code != httpx.codes.OK:
                raise SpotifyException('Unable to fetch playlist items')

            data = req.json()
            next_url = None

            if data.get('next'):
                parsed_next_url = parse_qs(urlparse(data.get('next')).query)
                next_url = f'/playlists/{playlist_id}' \
                           f'/tracks' \
                           f'?offset={parsed_next_url.get(b"offset")[0]}' \
                           f'&limit={parsed_next_url.get(b"limit")[0]}'

            items_parsed = []

            for item in data.get('items'):
                if item.get('is_local', False):
                    continue

                item = item.get('track')

                if next(filter(
                    lambda e: e.get('id') == item.get('id') and e.get('type') == item.get('type'),
                    items
                ), None):
                    continue

                if not item.get('is_playable', True):
                    continue

                image = next(iter(sorted(
                    item.get(
                        'show' if item.get('type') == 'episode' else 'album'
                    ).get('images'),
                    key=lambda i: i.get('height') or 0,
                    reverse=True
                )), None)

                if item.get('type') == 'episode':
                    show = {
                        'id': data.get('id'),
                        'name': item.get('show').get('name'),
                        'cover': image.get('url') if image else None,
                        'episodes': item.get('show').get('total_episodes')
                    }
                    iitem = {
                        'id': item.get('id'),
                        'name': item.get('name'),
                        'show': show
                    }

                    self.set_cache(f'episode:{iitem.get("id")}', iitem)
                    self.set_cache(f'show:{show.get("id")}', show)
                elif item.get('type') == 'track':
                    album = {
                        'id': item.get('album').get('id'),
                        'name': item.get('album').get('name'),
                        'cover': image.get('url') if image else None,
                        'tracks': item.get('album').get('total_tracks')
                    }
                    artists = [{
                        'id': a.get('id'),
                        'name': a.get('name')
                    } for a in item.get('artists')]

                    for a in artists:
                        self.set_cache(f'artist:{a.get("id")}', a)

                    iitem = {
                        'id': item.get('id'),
                        'name': item.get('name'),
                        'album': album,
                        'number': item.get('track_number') or 1,
                        'artists': artists,
                        'disc': item.get('disc_number') or 1
                    }

                    self.set_cache(f'track:{iitem.get("id")}', iitem)
                    self.set_cache(f'album:{album.get("id")}', album)
                else:
                    continue

                iitem = {**iitem, 'type': item.get('type')}
                items.append(iitem)
                items_parsed.append(iitem)

            self.set_cache(f'playlist:{playlist_id}:{self.md5credentials}:items_chunk', {
                'items': items,
                'next_url': next_url
            })

            for item_parsed in items_parsed:
                yield item_parsed

            if next_url:
                time.sleep(2)

        self.set_cache(f'playlist:{playlist_id}:{self.md5credentials}:items', items)

    @staticmethod
    def get_playable_id(item_id, item_type):
        if item_type == 'track':
            instance = TrackId
        elif item_type == 'episode':
            instance = EpisodeId
        else:
            raise SpotifyException('Not supported item type')

        return instance.from_uri(f'spotify:{item_type}:{item_id}')

    @contextmanager
    def get_stream(self, playable_id):
        try:
            stream = self.get_user_session().content_feeder().load(
                playable_id,
                VorbisOnlyAudioQuality(self.user_quality),
                False,
                None
            ).input_stream.stream()
        except RuntimeError:
            raise SpotifyException('Unable to fetch item stream')

        try:
            yield stream
        finally:
            stream.close()
