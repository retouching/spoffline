from pydantic import BaseModel


class Playlist(BaseModel):
    id: str
    name: str
    cover: str
    items: int
