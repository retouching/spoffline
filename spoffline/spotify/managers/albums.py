import time
from urllib.parse import parse_qs, urlparse

import httpx

from spoffline.helpers.exceptions import SpotifyException
from spoffline.models.album import Album
from spoffline.spotify.managers.manager import Manager


class Albums(Manager):
    def get(self, album_id, from_cache=True):
        if type(album_id) != str or len(album_id) < 1:
            raise SpotifyException('Invalid album id')

        if from_cache:
            album_or_exc = self.from_cache(album_id)

            if album_or_exc:
                if type(album_or_exc) == SpotifyException:
                    raise album_or_exc
                return album_or_exc

        with self.client.session.get_api_session() as session:
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
                self.set_cache(album_id, exc)
                self.set_cache(f'{album_id}:tracks', exc)

            raise exc

        return self.to_model(req.json())

    def get_tracks(self, album_id, from_cache=True):
        if type(album_id) != str or len(album_id) < 1:
            raise SpotifyException('Invalid album id')

        if from_cache:
            tracks_or_exc = self.from_cache(f'{album_id}:tracks')

            if tracks_or_exc:
                if type(tracks_or_exc) == SpotifyException:
                    raise tracks_or_exc

                for track in tracks_or_exc:
                    yield track

                return

            album_or_exc = self.from_cache(album_id)
            if album_or_exc and type(album_or_exc) == SpotifyException:
                raise album_or_exc

        album = self.get(album_id, from_cache)
        tracks = []
        next_url = f'/albums/{album_id}/tracks?offset=0&limit=50'

        if from_cache:
            saved_chunk = self.from_cache(f'{album_id}:tracks_chunk')
            if saved_chunk:
                tracks = saved_chunk.get('tracks')
                next_url = saved_chunk.get('next_url')

                for track in tracks:
                    yield track

        while next_url is not None:
            with self.client.session.get_api_session() as session:
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
                    lambda t: t.id == item.get('id'),
                    tracks
                ), None):
                    continue

                if not item.get('is_playable', True):
                    continue

                track = self.client.tracks.to_model(item, album)
                tracks.append(track)

            self.set_cache(f'{album_id}:tracks_chunk', {
                'tracks': tracks,
                'next_url': next_url
            })

            for track in filter(
                lambda t: t.id in [tt.get('id') for tt in data.get('items')],
                tracks
            ):
                yield track

            if next_url:
                time.sleep(2)

        self.set_cache(f'{album_id}:tracks', tracks)

    def to_model(self, data):
        image = next(iter(sorted(
            data.get('images'),
            key=lambda i: i.get('height') or 0,
            reverse=True
        )), None)

        album = Album(**{
            'id': data.get('id'),
            'name': data.get('name'),
            'cover': image.get('url') if image else None,
            'tracks': data.get('total_tracks')
        })

        self.set_cache(data.get('id'), album)

        return album
