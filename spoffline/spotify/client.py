import re
from contextlib import contextmanager

from librespot.audio.decoders import VorbisOnlyAudioQuality

from spoffline.helpers.exceptions import SpotifyException
from spoffline.helpers.paths import DefaultPaths
from spoffline.spotify.managers.albums import Albums
from spoffline.spotify.managers.artists import Artists
from spoffline.spotify.managers.playlists import Playlists
from spoffline.spotify.managers.session import Session
from spoffline.spotify.managers.tracks import Tracks


class Client:
    def __init__(
        self,
        email,
        password,
        cache_path=None
    ):
        self.cache_path = cache_path or DefaultPaths.get_cache_path()
        self.email = email
        self.password = password

        self.session = Session(self)
        self.tracks = Tracks(self)
        self.albums = Albums(self)
        self.artists = Artists(self)
        self.playlists = Playlists(self)

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
