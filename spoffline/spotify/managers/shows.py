import httpx

from spoffline.helpers.exceptions import SpotifyException
from spoffline.models.show import Show
from spoffline.spotify.managers.manager import Manager


class Shows(Manager):
    def get(self, show_id, from_cache=True):
        if type(show_id) != str or len(show_id) < 1:
            raise SpotifyException('Invalid show id')

        if from_cache:
            show_or_exc = self.from_cache(show_id)

            if show_or_exc:
                if type(show_or_exc) == SpotifyException:
                    raise show_or_exc
                return show_or_exc

        with self.client.session.get_api_session() as session:
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
                self.set_cache(show_id, exc)
                self.set_cache(f'{show_id}:episodes', exc)

            raise exc

        return self.to_model(req.json())

    def to_model(self, data):
        image = next(iter(sorted(
            data.get('images'),
            key=lambda i: i.get('height') or 0,
            reverse=True
        )), None)

        show = Show(**{
            'id': data.get('id'),
            'name': data.get('name'),
            'cover': image.get('url') if image else None,
            'episodes': data.get('total_episodes')
        })

        self.set_cache(data.get('id'), show)

        return show
