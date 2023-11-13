from pydantic import BaseModel


class Album(BaseModel):
    id: str
    name: str
    tracks: int
    cover: str | None = None
