import re

from pydantic import BaseModel


class Playlist(BaseModel):
    spotify_id: str
    name: str

    @property
    def filename(self):
        return re.sub(r' +', ' ', re.sub(r'[/\\:@?<>"]+', ' ', self.name))
