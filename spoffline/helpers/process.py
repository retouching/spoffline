import os
import random
import subprocess

from mutagen.id3 import APIC, ID3, TALB, TPE1, TRCK, TT2
from mutagen.mp3 import MP3

from spoffline.configuration import config
from spoffline.helpers.binaries import Binaries
from spoffline.models.song import Song
from spoffline.helpers.exceptions import FFMPEGException


def convert_to_mp3(filename, output, kbps=320):
    temp_file = os.path.join(config.paths.temp, f'{random.randbytes(16).hex()}.mp3')

    p = subprocess.Popen([
        Binaries.get('ffmpeg'),
        '-i', filename,
        '-c:a', 'libmp3lame',
        '-b:a', f'{kbps}k',
        '-y',
        temp_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return_code = p.wait()

    if return_code != 0:
        os.unlink(temp_file)
        raise FFMPEGException('Unable to convert file')

    if os.path.exists(output):
        os.unlink(output)

    os.rename(temp_file, output)


def apply_metadata(filename, song):
    if type(song) != Song:
        raise ValueError('You must supply a valid song instance to use')

    handler = MP3(filename)
    handler.delete()
    handler.save()

    if handler.tags is None:
        handler.add_tags()

    handler.tags['TT2'] = TT2(encoding=3, text=song.name)
    handler.tags['TPE1'] = TPE1(encoding=3, text=song.artists)
    handler.tags['TIT2'] = TALB(encoding=3, text=song.name)
    handler.tags['TALB'] = TALB(encoding=3, text=song.album)
    handler.tags['APIC'] = APIC(
        encoding=0,
        mime=f'image/{song.cover.ext}',
        type=3,
        desc=u'Cover',
        data=song.cover.data
    )

    handler.save()
