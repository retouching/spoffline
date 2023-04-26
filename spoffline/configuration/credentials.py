from pydantic import BaseModel


class CredentialsConfiguration(BaseModel):
    email: str
    password: str
