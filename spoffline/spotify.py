import httpx

from spoffline.cacher import Cacher
from spoffline.configuration import config
from spoffline.helpers.exceptions import SpotifyException
from spoffline.models.song import Song, SongCover


class Spotify:
    def __init__(self):
        self.cache = Cacher('spotify')

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

    def get_track_infos(self, track_id):
        song = self.cache.get(f'song:infos:{track_id}')
        if song:
            return song

        with httpx.Client() as client:
            req = client.get(
                f'https://api.spotify.com/v1/tracks/{track_id}',
                headers={'Authorization': f'Bearer {self.get_api_token()}'}
            )

        if req.status_code != httpx.codes.OK:
            raise SpotifyException(f'Unable to fetch track info (HTTP code: {req.status_code})')

        data = req.json()

        image = next(iter(sorted(
            data.get('album').get('images'),
            key=lambda i: i.get('height'),
            reverse=True
        ))).get('url')

        with httpx.Client() as client:
            req = client.get(image)

        if req.status_code != httpx.codes.OK:
            raise SpotifyException(f'Unable to fetch track cover (HTTP code: {req.status_code})')

        song = Song(
            id=data.get('id'),
            name=data.get('name'),
            artists=[a.get('name') for a in data.get('artists')],
            album=data.get('album').get('name'),
            cover=SongCover(
                data=req.content,
                ext=req.headers.get('Content-Type').split('/').pop()
            )
        )

        self.cache.set(f'song:infos:{track_id}', song, 60 * 60 * 24 * 7)

        return song
