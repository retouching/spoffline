import re
from contextlib import contextmanager

from librespot.audio.decoders import VorbisOnlyAudioQuality

from spoffline.helpers.exceptions import SpotifyException
from spoffline.spotify.managers.albums import Albums
from spoffline.spotify.managers.artists import Artists
from spoffline.spotify.managers.session import Session
from spoffline.spotify.managers.shows import Shows
from spoffline.spotify.managers.tracks import Tracks


class Client:
    def __init__(self):
        self.session = Session(self)
        self.tracks = Tracks(self)
        self.albums = Albums(self)
        self.artists = Artists(self)
        self.shows = Shows(self)

    @staticmethod
    def parse_url(url):
        match = re.match(
            r'https?://open\.spotify\.com/(album|artist|episode|playlist|track|show)/([^?]+)',
            url
        )

        if not match:
            raise SpotifyException('Invalid URL provided')

        return match.group(2), match.group(1)

    @contextmanager
    def get_stream(self, playable_id):
        try:
            stream = self.session.session.content_feeder().load(
                playable_id,
                VorbisOnlyAudioQuality(self.session.user.audio_quality),
                False,
                None
            ).input_stream.stream()
        except RuntimeError:
            raise SpotifyException('Unable to fetch item stream')

        try:
            yield stream
        finally:
            stream.close()
