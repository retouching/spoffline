import time
from urllib.parse import parse_qs, urlparse

import httpx

from spoffline.helpers.exceptions import SpotifyException
from spoffline.models.playlist import Playlist
from spoffline.spotify.managers.manager import Manager


class Playlists(Manager):
    def get(self, playlist_id, from_cache=True):
        if type(playlist_id) != str or len(playlist_id) < 1:
            raise SpotifyException('Invalid playlist id')

        if from_cache:
            playlist_or_exc = self.from_cache(f'{playlist_id}:{self.client.session.credentials.hashed}')

            if playlist_or_exc:
                if type(playlist_or_exc) == SpotifyException:
                    raise playlist_or_exc
                return playlist_or_exc

        with self.client.session.get_api_session() as session:
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
                self.set_cache(f'{playlist_id}:{self.client.session.credentials.hashed}', exc)
                self.set_cache(f'{playlist_id}:{self.client.session.credentials.hashed}:items', exc)

            raise exc

        return self.to_model(req.json())

    def get_items(self, playlist_id, from_cache=True):
        if type(playlist_id) != str or len(playlist_id) < 1:
            raise SpotifyException('Invalid playlist id')

        if from_cache:
            items_or_exc = self.from_cache(f'{playlist_id}:{self.client.session.credentials.hashed}:items')

            if items_or_exc:
                if type(items_or_exc) == SpotifyException:
                    raise items_or_exc

                for item in items_or_exc:
                    yield item

                return

            playlist_or_exc = self.from_cache(f'{playlist_id}:{self.client.session.credentials.hashed}')
            if playlist_or_exc and type(playlist_or_exc) == SpotifyException:
                raise playlist_or_exc

        items = []
        next_url = f'/playlists/{playlist_id}/tracks?offset=0&limit=50'

        if from_cache:
            saved_chunk = self.from_cache(f'{playlist_id}:{self.client.session.credentials.hashed}:items_chunk')
            if saved_chunk:
                items = saved_chunk.get('items')
                next_url = saved_chunk.get('next_url')

                for item in items:
                    yield item

        while next_url is not None:
            with self.client.session.get_api_session() as session:
                req = session.get(next_url)

            if req.status_code != httpx.codes.OK:
                raise SpotifyException('Unable to fetch playlist items')

            data = req.json()
            next_url = None

            if data.get('next'):
                parsed_next_url = parse_qs(urlparse(data.get('next')).query)
                next_url = f'/playlists/{playlist_id}' \
                           f'/tracks' \
                           f'?offset={parsed_next_url.get("offset")[0]}' \
                           f'&limit={parsed_next_url.get("limit")[0]}'

            for item in data.get('items'):
                if item.get('is_local', False):
                    continue

                item = item.get('track')

                if next(filter(
                    lambda i: i.id == item.get('id'),
                    items
                ), None):
                    continue

                if not item.get('is_playable', True):
                    continue

                if item.get('type') != 'track':
                    continue

                track = self.client.tracks.to_model(item)
                items.append(track)

            self.set_cache(f'{playlist_id}:{self.client.session.credentials.hashed}:items_chunk', {
                'items': items,
                'next_url': next_url
            })

            for item in filter(
                lambda i: i.id in [ii.get('track').get('id') for ii in data.get('items')],
                items
            ):
                yield item

            if next_url:
                time.sleep(2)

        self.set_cache(f'{playlist_id}:{self.client.session.credentials.hashed}:items', items)

    def to_model(self, data):
        image = next(iter(sorted(
            data.get('images'),
            key=lambda i: i.get('height') or 0,
            reverse=True
        )), None)

        playlist = Playlist(**{
            'id': data.get('id'),
            'name': data.get('name'),
            'cover': image.get('url') if image else None,
            'items': data.get('tracks').get('total')
        })

        self.set_cache(f'{data.get("id")}:{self.client.session.credentials.hashed}', playlist)

        return playlist
