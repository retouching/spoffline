from ffdevine.helpers.enums.enum import CustomEnum


class Codec(CustomEnum):
    @property
    def extension(self):
        return self.value.lower().replace('.', '').replace('-', '')

    @staticmethod
    def from_string(codec, strict=False):
        raise NotImplemented
