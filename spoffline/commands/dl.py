import os
import re
import time

import click
from httpx import HTTPError
from librespot.audio.decoders import AudioQuality
from librespot.core import Session
from mutagen import MutagenError
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeRemainingColumn

from spoffline.configuration import config
from spoffline.console import console
from spoffline.helpers import process
from spoffline.helpers.exceptions import FFMPEGException, SpotifyException
from spoffline.spotify import Spotify


@click.command()
@click.argument('url')
@click.pass_context
def cli(ctx, url):
    """Download content from Spotify"""

    try:
        url_id, url_type = Spotify.parse_url(url)
    except SpotifyException:
        return console.error('Error: Invalid URL provided')

    with console.status(
        '[white]Connect to account ...',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            ctx.client = Spotify()
        except Session.SpotifyAuthenticationException as e:
            return console.error(f'Error: Spotify return bad response ({e})')

    console.print(
        f'Welcome back, [info]{ctx.client.user_data.get("display_name")}',
        style='white'
    )

    if url_type == 'track':
        download_track(ctx, url_id)

    elif url_type == 'album':
        download_album(ctx, url_id)

    else:
        console.error(f'Error: {url_type}s not handled yet')


def download_track(ctx, url_id, album_name=None):
    with console.status(
        '[white]Fetching track data ...',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            track = ctx.client.get_track(url_id)
        except SpotifyException as e:
            time.sleep(1)
            return console.error(f'Error: {e}')

    console.print(
        f'Starting download of '
        f'[info]{track.get("name")}[/info]'
        f' by '
        f'[info]{"[/info], [info]".join([a.get("name") for a in track.get("artists")])}[/info]',
        style='white'
    )

    temp_file = os.path.join(config.paths.temp, f'{track.get("id")}.ogg')
    if os.path.exists(temp_file):
        os.unlink(temp_file)

    with ctx.client.get_stream(Spotify.get_playable_id(url_id, 'track')) as stream:
        total_size = stream.size()

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(compact=True),
            transient=True,
            console=console
        ) as progress:
            task = progress.add_task('[white]Downloading [info]ogg file[/info]', total=total_size)

            with open(temp_file, 'w+b') as f:
                while True:
                    data = stream.read(8192)
                    if not data:
                        break
                    progress.advance(task, f.write(data))

    with console.status(
        '[white]Converting [info]ogg file[/info] to [info]mp3 file',
        spinner_style='info',
        spinner='arc'
    ):
        temp_mp3_file = os.path.join(config.paths.temp, f'{track.get("id")}.mp3')
        if os.path.exists(temp_mp3_file):
            os.unlink(temp_mp3_file)

        try:
            process.convert_to_mp3(
                temp_file,
                temp_mp3_file,
                ctx.client.user_quality == AudioQuality.VERY_HIGH
            )
        except FFMPEGException:
            return console.error('Error: Unable to convert file')

    with console.status(
        '[white]Applying [info]metadata',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            process.apply_mp3_metadata(
                temp_mp3_file,
                name=track.get('name'),
                artists=[a.get('name') for a in track.get('artists')],
                cover_url=track.get('album').get('cover'),
                track_no=track.get('number'),
                album=track.get('album').get('name')
            )
        except (MutagenError, HTTPError):
            return console.error('Error: Unable to apply metadata to file')

    with console.status(
        '[white]Cleaning [info]files',
        spinner_style='info',
        spinner='arc'
    ):
        def clean_string(text):
            return re.sub(r' +', ' ', re.sub(r'[/\\:@?<>"]+', ' ', text))

        artist = 'Unknown'
        if len(track.get("artists")) > 0:
            artist = clean_string(track.get("artists")[0].get('name'))

        final_filename = f'{clean_string(track.get("name"))} - {artist}.mp3'

        final_file = os.path.join(*[
            f for f in [
                config.paths.downloads,
                clean_string(album_name) if album_name else None,
                final_filename
            ] if f is not None
        ])

        if not os.path.exists(os.path.dirname(final_file)):
            os.makedirs(os.path.dirname(final_file), exist_ok=True)

        if os.path.exists(final_file):
            os.unlink(final_file)

        os.rename(temp_mp3_file, final_file)
        os.unlink(temp_file)

    console.print(
        f'Successfully downloaded '
        f'[info]{track.get("name")}[/info]'
        f' by '
        f'[info]{"[/info], [info]".join([a.get("name") for a in track.get("artists")])}[/info]',
        style='white'
    )


def download_album(ctx, album_id):
    with console.status(
        '[white]Fetching album data ...',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            album = ctx.client.get_album(album_id)
        except SpotifyException as e:
            time.sleep(1)
            return console.error(f'Error: {e}')

    console.print(
        f'Starting download of '
        f'[info]{album.get("name")}',
        style='white'
    )

    console.rule()

    for index, track in enumerate(ctx.client.get_album_tracks(album_id)):
        download_track(ctx, track.get('id'), album.get('name'))

        console.rule(
            f'[info]Download progress: {index+1}/{album.get("tracks")}'
        )

    console.print(
        f'Successfully downloaded '
        f'[info]{album.get("name")}',
        style='white'
    )
