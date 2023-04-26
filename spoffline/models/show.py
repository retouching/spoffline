from pydantic import BaseModel


class Show(BaseModel):
    id: str
    name: str
    cover: str
    episodes: int
