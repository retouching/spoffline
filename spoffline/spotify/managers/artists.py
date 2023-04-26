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

    def to_model(self, data):
        artist = Artist(**{
            'id': data.get('id'),
            'name': data.get('name')
        })

        self.set_cache(data.get('id'), artist)

        return artist
