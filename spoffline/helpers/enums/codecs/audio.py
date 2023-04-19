from ffdevine.helpers.enums.codecs.codec import Codec
from ffdevine.helpers.exceptions import CodecNotFoundException


class AudioCodec(Codec):
    """
    From: https://github.com/devine-dl/devine/blob/master/devine/core/tracks/audio.py
    """

    AAC = 'AAC'
    AC3 = 'DD'
    EC3 = 'DD+'
    OPUS = 'OPUS'
    OGG = 'VORB'
    DTS = 'DTS'
    ALAC = 'ALAC'
    UKN = 'Unknown'

    @staticmethod
    def from_string(codec, strict=False):
        if not isinstance(codec, str):
            raise ValueError('Codec must be a string')

        codec = codec.lower().strip().split('.')[0]

        if codec == 'mp4a':
            return AudioCodec.AAC
        if codec == 'ac-3':
            return AudioCodec.AC3
        if codec == 'ec-3':
            return AudioCodec.EC3
        if codec == 'opus':
            return AudioCodec.OPUS
        if codec == 'dtsc':
            return AudioCodec.DTS
        if codec == 'alac':
            return AudioCodec.ALAC

        if strict:
            raise CodecNotFoundException(f'Unable to resolve {codec}')

        return AudioCodec.UKN
