from ffdevine.helpers.enums.codecs.codec import Codec
from ffdevine.helpers.exceptions import CodecNotFoundException


class SubtitleCodec(Codec):
    """
    From: https://github.com/devine-dl/devine/blob/master/devine/core/tracks/subtitle.py
    """

    SubRip = 'SRT'
    SubStationAlpha = 'SSA'
    SubStationAlphav4 = 'ASS'
    TimedTextMarkupLang = 'TTML'
    WebVTT = 'VTT'
    FTTML = 'STPP'
    FVTT = 'WVTT'
    UKN = 'Unknown'

    @staticmethod
    def from_string(codec, strict=False):
        if not isinstance(codec, str):
            raise ValueError('Codec must be a string')

        codec = codec.lower().strip().split('.')[0]

        if codec == 'srt':
            return SubtitleCodec.SubRip
        elif codec == 'ssa':
            return SubtitleCodec.SubStationAlpha
        elif codec == 'ass':
            return SubtitleCodec.SubStationAlphav4
        elif codec == 'ttml':
            return SubtitleCodec.TimedTextMarkupLang
        elif codec == 'vtt':
            return SubtitleCodec.WebVTT
        elif codec == 'stpp':
            return SubtitleCodec.FTTML
        elif codec == 'wvtt':
            return SubtitleCodec.FVTT

        if strict:
            raise CodecNotFoundException(f'Unable to resolve {codec}')

        return SubtitleCodec.UKN
