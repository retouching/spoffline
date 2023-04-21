import os.path
import re

import click
from librespot.audio.decoders import AudioQuality
from tqdm import tqdm

from spoffline.configuration import config
from spoffline.helpers import process
from spoffline.helpers.exceptions import SpotifyException
from spoffline.spotify import Spotify


client = Spotify()


@click.command()
@click.argument('url')
def cli(url):
    """
    Download content from spotify

    URL: URL to content to download
    """
    try:
        parsed_url = Spotify.parse_url(url)
    except SpotifyException:
        raise click.BadParameter('Invalid url provided')

    click.clear()

    if parsed_url.get('track_id'):
        download_track(parsed_url.get('track_id'))


def download_track(track_id):
    print('Fetching track informations ...')
    try:
        track = client.get_track(track_id)
    except SpotifyException as e:
        return print(f'Error: {e}')

    print(f'Starting download of {track.get("name")} by {next(iter(track.get("artists"))).get("name")}')

    print('Downloading ogg file ...')

    temp_file = os.path.join(config.paths.temp, f'{track.get("id")}.ogg')
    if os.path.exists(temp_file):
        os.unlink(temp_file)

    with client.get_stream(Spotify.get_playable_id(track_id, 'track')) as stream:
        total_size = stream.size()

        with open(temp_file, 'w+b') as f:
            with tqdm(
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                total=total_size,
                bar_format='{percentage:3.0f}%|{bar:16}|{n_fmt} / {total_fmt} | {rate_fmt}, ETA {remaining}'
            ) as tbar:
                while True:
                    data = stream.read(8192)
                    if not data:
                        break
                    tbar.update(f.write(data))

    print('Converting ogg file to mp3 ...')

    temp_mp3_file = os.path.join(config.paths.temp, f'{track.get("id")}.mp3')
    if os.path.exists(temp_mp3_file):
        os.unlink(temp_mp3_file)

    process.convert_to_mp3(temp_file, temp_mp3_file, client.user_quality == AudioQuality.VERY_HIGH)

    print('Applying metadata ...')

    process.apply_mp3_metadata(
        temp_mp3_file,
        name=track.get('name'),
        artists=[a.get('name') for a in track.get('artists')],
        cover_url=track.get('album').get('cover'),
        track_no=track.get('number')
    )

    print('Cleaning files ...')

    trackname_clean = re.sub(r' +', ' ', re.sub(r'[/\\:@?<>"]+', ' ', track.get('name')))
    author_clean = re.sub(r' +', ' ', re.sub(r'[/\\:@?<>"]+', ' ', next(iter(track.get("artists"))).get("name")))

    final_file = os.path.join(
        config.paths.downloads,
        f'{trackname_clean} - {author_clean}.mp3'
    )

    os.rename(temp_mp3_file, final_file)
    os.unlink(temp_file)

    print(f'Successfully downloaded {track.get("name")} by {next(iter(track.get("artists"))).get("name")}')
