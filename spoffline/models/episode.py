import re

from pydantic import BaseModel

from spoffline.models.show import Show


class Episode(BaseModel):
    spotify_id: str
    name: str
    show: Show
    description: str

    @property
    def filename(self):
        return re.sub(r' +', ' ', re.sub(r'[/\\:@?<>"]+', ' ', self.name))
