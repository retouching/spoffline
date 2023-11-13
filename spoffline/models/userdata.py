from librespot.audio.decoders import AudioQuality
from pydantic import BaseModel


class UserData(BaseModel):
    country: str
    display_name: str
    product: str

    @property
    def audio_quality(self):
        return AudioQuality.VERY_HIGH if self.product == 'premium' else AudioQuality.HIGH
