import httpx

from spoffline.helpers.exceptions import SpotifyException
from spoffline.models.track import Track
from spoffline.spotify.managers.manager import Manager


class Tracks(Manager):
    def get(self, track_id, from_cache=True):
        if type(track_id) != str or len(track_id) < 1:
            raise SpotifyException('Invalid track id')

        if from_cache:
            track_or_exc = self.from_cache(track_id)

            if track_or_exc:
                if type(track_or_exc) == SpotifyException:
                    raise track_or_exc
                return track_or_exc

        with self.client.session.get_api_session() as session:
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
                self.set_cache(track_id, exc)

            raise exc

        data = req.json()

        if not data.get('is_playable', True):
            raise SpotifyException('This track is not available in your country')

        return self.to_model(data)

    def to_model(self, data, album=None, artists=None):
        if not album:
            if not data.get('album'):
                raise SpotifyException('No album provided')
            album = self.client.albums.to_model(data.get('album'))

        if not artists:
            if not data.get('artists'):
                raise SpotifyException('No artists provided')
            artists = [self.client.artists.to_model(a) for a in data.get('artists')]

        track = Track(**{
            'id': data.get('id'),
            'name': data.get('name'),
            'number': data.get('track_number') or 1,
            'disc': data.get('disc_number') or 1,
            'album': album,
            'artists': artists
        })

        self.set_cache(data.get('id'), track)

        return track
