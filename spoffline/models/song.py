import hashlib
import os.path
import re
from typing import List

from pydantic import BaseModel


class Song(BaseModel):
    id: str
    name: str
    artists: List[str]
    album: str
    cover_url: str

    @property
    def filename(self):
        return re.sub(r' +', ' ', re.sub(r'[/\\:@?<>"]+', ' ', self.name))

    @property
    def album_art_filename(self):
        md5 = hashlib.md5()
        md5.update(self.album.lower().encode())
        album_id = md5.hexdigest()

        return f'{album_id}.jpg'
