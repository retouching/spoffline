from pydantic import BaseModel, constr


class CredentialsConfiguration(BaseModel):
    client_id: str
    client_secret: str
    email: str
    password: str
    is_premium: bool
    market: constr(regex=r'^[A-Z]{2}$') | None = None
