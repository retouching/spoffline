import hashlib
import mimetypes
import os
import random
import subprocess

import httpx
from mutagen.id3 import APIC, TALB, TEN, TPE1, TPOS, TRCK, TT2
from mutagen.mp3 import MP3

from spoffline.helpers.binaries import Binaries
from spoffline.helpers.exceptions import FFMPEGException
from spoffline.helpers.paths import DefaultPaths


def convert_to_mp3(filename, output, is_premium=False):
    temp_file = os.path.join(DefaultPaths.get_temp_path(), f'{random.randbytes(16).hex()}.mp3')

    p = subprocess.Popen([
        Binaries.get('ffmpeg'),
        '-i', filename,
        '-c:a', 'libmp3lame',
        '-b:a', f'{320 if is_premium else 160}k',
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


def apply_mp3_metadata(filename, *, name=None, artists=None, album=None, cover_url=None, track_no=None, disc_no=None):
    mimetype, _ = mimetypes.guess_type(filename)

    if mimetype != 'audio/mpeg':
        raise ValueError('Only mp3 file can be processed')

    handler = MP3(filename)
    handler.delete()
    handler.save()

    if handler.tags is None:
        handler.add_tags()

    handler.tags['TEN'] = TEN(encoding=3, text='spoffline v1.0.0')

    if disc_no:
        handler.tags['TPOS'] = TPOS(encoding=3, text=str(disc_no))

    if track_no:
        handler.tags['TRCK'] = TRCK(encoding=3, text=str(track_no))

    if name:
        handler.tags['TT2'] = TT2(encoding=3, text=name)

    if artists:
        if type(artists) != list or next(filter(
            lambda a: type(a) != str,
            artists
        ), None):
            raise ValueError('Invalid artists metadata found')
        handler.tags['TPE1'] = TPE1(encoding=3, text=artists)

    if album:
        handler.tags['TALB'] = TALB(encoding=3, text=album)

    if cover_url:
        cache_cover_name = hashlib.md5()
        cache_cover_name.update(cover_url.encode())
        cache_cover_name = cache_cover_name.hexdigest()

        album_art_path = os.path.join(DefaultPaths.get_cache_path(), 'spotify/covers', f'{cache_cover_name}.jpg')
        if not os.path.exists(album_art_path):
            os.makedirs(os.path.dirname(album_art_path), exist_ok=True)

            with httpx.Client() as client:
                req = client.get(cover_url)
                req.raise_for_status()

            with open(album_art_path, 'w+b') as f:
                f.write(req.content)

        with open(album_art_path, 'rb') as f:
            handler.tags['APIC'] = APIC(
                encoding=0,
                mime='image/jpg',
                type=3,
                desc=u'Cover',
                data=f.read()
            )

    handler.save()
