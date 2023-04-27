import time
from urllib.parse import parse_qs, urlparse

import httpx

from spoffline.helpers.exceptions import SpotifyException
from spoffline.models.artist import Artist
from spoffline.spotify.managers.manager import Manager


class Artists(Manager):
    def get(self, artist_id, from_cache=True):
        if type(artist_id) != str or len(artist_id) < 1:
            raise SpotifyException('Invalid artist id')

        if from_cache:
            artist_or_exc = self.from_cache(artist_id)

            if artist_or_exc:
                if type(artist_or_exc) == SpotifyException:
                    raise artist_or_exc
                return artist_or_exc

        with self.client.session.get_api_session() as session:
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
                self.set_cache(artist_id, exc)

            raise exc

        return self.to_model(req.json())

    def get_albums(self, artist_id, from_cache=True):
        if type(artist_id) != str or len(artist_id) < 1:
            raise SpotifyException('Invalid artist id')

        if from_cache:
            artist_albums_or_exc = self.from_cache(f'{artist_id}:albums')

            if artist_albums_or_exc:
                if type(artist_albums_or_exc) == SpotifyException:
                    raise artist_albums_or_exc

                for album in artist_albums_or_exc:
                    yield album

                return

            artist_or_exc = self.from_cache(artist_id)
            if artist_or_exc and type(artist_or_exc) == SpotifyException:
                raise artist_or_exc

        albums = []
        next_url = f'/artists/{artist_id}/albums?offset=0&limit=50&include_groups=album,single'

        if from_cache:
            saved_chunk = self.from_cache(f'{artist_id}:albums_chunk')
            if saved_chunk:
                albums = saved_chunk.get('albums')
                next_url = saved_chunk.get('next_url')

                for album in albums:
                    yield album

        while next_url is not None:
            with self.client.session.get_api_session() as session:
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
                           f'&limit={parsed_next_url.get("limit")[0]}' \
                           f'&include_groups=album,single'

            for item in data.get('items'):
                if next(filter(
                    lambda a: a.id == item.get('id'),
                    albums
                ), None):
                    continue

                album = self.client.albums.to_model(item)
                albums.append(album)

            self.set_cache(f'{artist_id}:albums_chunk', {
                'albums': albums,
                'next_url': next_url
            })

            for album in filter(
                lambda a: a.id in [aa.get('id') for aa in data.get('items')],
                albums
            ):
                yield album

            if next_url:
                time.sleep(2)

        self.set_cache(f'{artist_id}:albums', albums)

    def to_model(self, data):
        artist = Artist(**{
            'id': data.get('id'),
            'name': data.get('name')
        })

        self.set_cache(data.get('id'), artist)

        return artist
