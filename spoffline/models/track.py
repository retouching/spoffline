from typing import List

from librespot.metadata import TrackId
from pydantic import BaseModel

from spoffline.models.album import Album
from spoffline.models.artist import Artist


class Track(BaseModel):
    id: str
    name: str
    artists: List[Artist]
    album: Album
    number: int = 1
    disc: int = 1

    @property
    def playable_id(self):
        return TrackId.from_uri(f'spotify:track:{self.id}')
