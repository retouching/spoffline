import subprocess

from spoffline.spotify.client import Client


EMAIL = 'xxx@xxx.com'
PASSWORD = 'xxx'
TRACK_URL = 'xxx'


def main():
    # Create client
    client = Client(email=EMAIL, password=PASSWORD, cache_path='./cache')

    # Get track id (function return tuple with url id and url type)
    track_id, _ = Client.parse_url(TRACK_URL)

    # Get track data
    track = client.tracks.get(track_id)

    print(f'Playing: {track.name} from {track.album.name} by {", ".join([a.name for a in track.artists])}')

    # spawn ffplay
    ffplay = subprocess.Popen(
        ["ffplay", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Get track stream and send it to ffplay
    with client.get_stream(track.playable_id) as stream:
        while True:
            byte = stream.read(1)
            if byte == -1:
                return
            ffplay.stdin.write(byte)


if __name__ == '__main__':
    main()
