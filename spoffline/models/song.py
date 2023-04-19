import re
from typing import List

from pydantic import BaseModel


class SongCover(BaseModel):
    data: bytes
    ext: str


class Song(BaseModel):
    id: str
    name: str
    artists: List[str]
    album: str
    cover: SongCover

    @property
    def filename(self):
        return re.sub(r' +', ' ', re.sub(r'[/\\:@?<>"]+', ' ', self.name))
