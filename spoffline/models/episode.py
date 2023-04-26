from librespot.metadata import EpisodeId
from pydantic import BaseModel

from spoffline.models.show import Show


class Episode(BaseModel):
    id: str
    name: str
    show: Show

    @property
    def playable_id(self):
        return EpisodeId.from_uri(f'spotify:episode:{self.id}')
