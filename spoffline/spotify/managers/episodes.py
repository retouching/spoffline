import httpx
from rich import print as pprint

from spoffline.helpers.exceptions import SpotifyException
from spoffline.models.episode import Episode
from spoffline.spotify.managers.manager import Manager


class Episodes(Manager):
    def get(self, episode_id, from_cache=True):
        if type(episode_id) != str or len(episode_id) < 1:
            raise SpotifyException('Invalid episode id')

        if from_cache:
            episode_or_exc = self.from_cache(episode_id)

            if episode_or_exc:
                if type(episode_or_exc) == SpotifyException:
                    raise episode_or_exc
                return episode_or_exc

        with self.client.session.get_api_session() as session:
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
                self.set_cache(episode_id, exc)

            raise exc

        pprint(req.json())
        return self.to_model(req.json())

    def to_model(self, data, show=None):
        if not show:
            if not data.get('show'):
                raise SpotifyException('No show provided')
            show = self.client.shows.to_model(data.get('show'))

        episode = Episode(**{
            'id': data.get('id'),
            'name': data.get('name'),
            'show': show
        })

        self.set_cache(data.get('id'), episode)

        return episode
