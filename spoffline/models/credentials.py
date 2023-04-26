import hashlib

from pydantic import BaseModel


class Credentials(BaseModel):
    email: str
    password: str

    @property
    def hashed(self):
        hash_credentials = hashlib.md5()
        hash_credentials.update(f'{self.email}:{self.password}'.encode())
        return hash_credentials.hexdigest()
