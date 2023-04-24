from pydantic import BaseModel, constr


class CredentialsConfiguration(BaseModel):
    client_id: str
    client_secret: str
    email: str
    password: str
