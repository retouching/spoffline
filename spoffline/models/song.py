import re
from typing import List

from pydantic import BaseModel

from spoffline.models.album import Album
from spoffline.models.artist import Artist


class Song(BaseModel):
    spotify_id: str
    name: str
    album: Album
    artists: List[Artist]
    track_no: int = 1

    @property
    def filename(self):
        return re.sub(r' +', ' ', re.sub(r'[/\\:@?<>"]+', ' ', self.name))
