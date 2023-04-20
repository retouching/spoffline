import re

from pydantic import BaseModel


class Album(BaseModel):
    spotify_id: str
    cover_url: str | None = None
    name: str

    @property
    def filename(self):
        return re.sub(r' +', ' ', re.sub(r'[/\\:@?<>"]+', ' ', self.name))
