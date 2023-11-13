import subprocess
import time

from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn

from spoffline.spotify.client import Client


EMAIL = 'xxx@xxx.com'
PASSWORD = 'xxx'
TRACK_URL = 'xxx'


def main():
    """
    Stream music on ffplay
    """

    # Create client
    client = Client(email=EMAIL, password=PASSWORD, cache_path='./cache')

    # Get track id (function return tuple with url id and url type)
    track_id, _ = Client.parse_url(TRACK_URL)

    # Get track data
    track = client.tracks.get(track_id)

    print(f'Playing: {track.name} from {track.album.name} by {", ".join([a.name for a in track.artists])}')

    # spawn ffplay
    ffplay = subprocess.Popen(
        ['ffplay', '-autoexit', '-'],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Get track stream and send it to ffplay
    with client.get_stream(track.playable_id) as stream:
        total_size = stream.size()

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=True
        ) as progress:
            task = progress.add_task('Progress', total=total_size)

            while True:
                data = stream.read(8196)
                if not data:
                    break
                progress.advance(task, ffplay.stdin.write(data))

    # Wait a little and kill process
    time.sleep(5)
    if not ffplay.returncode:
        ffplay.kill()


if __name__ == '__main__':
    main()


