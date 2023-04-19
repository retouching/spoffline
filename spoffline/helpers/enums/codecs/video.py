from ffdevine.helpers.enums.codecs.codec import Codec
from ffdevine.helpers.exceptions import CodecNotFoundException


class VideoCodec(Codec):
    """
    From: https://github.com/devine-dl/devine/blob/master/devine/core/tracks/video.py
    """

    AVC = 'H.264'
    HEVC = 'H.265'
    VC1 = 'VC-1'
    VP8 = 'VP8'
    VP9 = 'VP9'
    AV1 = 'AV1'
    UKN = 'Unknown'

    @staticmethod
    def from_string(codec, strict=False):
        if not isinstance(codec, str):
            raise ValueError('Codec must be a string')

        codec = codec.lower().strip().split('.')[0]

        if codec in [
            'avc1', 'avc2', 'avc3', 'dva1', 'dvav'
        ]:
            return VideoCodec.AVC

        if codec in [
            'hev1', 'hev2', 'hev3', 'hvc1', 'hvc2', 'hvc3',
            'dvh1', 'dvhe',
            'lhv1', 'lhe1'
        ]:
            return VideoCodec.HEVC

        if codec == 'vc-1':
            return VideoCodec.VC1

        if codec in ['vp08', 'vp8']:
            return VideoCodec.VP8
        if codec in ['vp09', 'vp9']:
            return VideoCodec.VP9
        if codec == 'av01':
            return VideoCodec.AV1

        if strict:
            raise CodecNotFoundException(f'Unable to resolve {codec}')

        return VideoCodec.UKN
