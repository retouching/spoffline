import os
import re
import time

import click
from httpx import HTTPError
from librespot.audio.decoders import AudioQuality
from librespot.core import Session
from mutagen import MutagenError
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeRemainingColumn

from spoffline.configuration import Configuration
from spoffline.console import console
from spoffline.helpers import process
from spoffline.helpers.exceptions import ConfigurationException, FFMPEGException, SpotifyException
from spoffline.helpers.paths import DefaultPaths
from spoffline.spotify.client import Client


@click.command()
@click.argument('url')
@click.pass_context
def cli(ctx, url):
    """Download content from Spotify"""

    try:
        config = Configuration.load()
    except ConfigurationException:
        return console.error('Error: You must create configuration before downloading content')

    try:
        url_id, url_type = Client.parse_url(url)
    except SpotifyException:
        return console.error('Error: Invalid URL provided')

    ctx.client = Client(
        config.email,
        config.password
    )

    with console.status(
        '[white]Connect to account ...',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            ctx.client.session.get_api_session()
        except Session.SpotifyAuthenticationException as e:
            return console.error(f'Error: Spotify return bad response ({e})')

    console.print(
        f'Welcome back, [info]{ctx.client.session.user.display_name}',
        style='white'
    )

    if url_type == 'track':
        download_track(ctx, url_id)

    elif url_type == 'album':
        download_album(ctx, url_id)

    elif url_type == 'playlist':
        download_playlist(ctx, url_id)

    elif url_type == 'artist':
        download_discography(ctx, url_id)

    else:
        console.error(f'Error: {url_type}s not handled yet')


def download_track(ctx, track_id, *, album_name=None, playlist_name=None, artist_name=None):
    with console.status(
        '[white]Fetching track data ...',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            track = ctx.client.tracks.get(track_id)
        except SpotifyException as e:
            time.sleep(1)
            return console.error(f'Error: {e}')

    console.print(
        f'Starting download of '
        f'[info]{track.name}[/info]'
        f' by '
        f'[info]{"[/info], [info]".join([a.name for a in track.artists])}[/info]',
        style='white'
    )

    temp_file = os.path.join(DefaultPaths.get_temp_path(), f'{track.id}.ogg')
    if os.path.exists(temp_file):
        os.unlink(temp_file)

    with ctx.client.get_stream(track.playable_id) as stream:
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
        temp_mp3_file = os.path.join(DefaultPaths.get_temp_path(), f'{track.id}.mp3')
        if os.path.exists(temp_mp3_file):
            os.unlink(temp_mp3_file)

        try:
            process.convert_to_mp3(
                temp_file,
                temp_mp3_file,
                ctx.client.session.user.audio_quality == AudioQuality.VERY_HIGH
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
                name=track.name,
                artists=[a.name for a in track.artists],
                cover_url=track.album.cover,
                track_no=track.number,
                album=track.album.name
            )
        except (MutagenError, HTTPError):
            return console.error('Error: Unable to apply metadata to file')

    with console.status(
        '[white]Cleaning [info]files',
        spinner_style='info',
        spinner='arc'
    ):
        def clean_string(text):
            return re.sub(r' +', ' ', re.sub(r'[/\\:@?<>"*]+', ' ', text))

        artist = 'Unknown'
        if len(track.artists) > 0:
            artist = clean_string(track.artists[0].name)

        final_filename = f'{clean_string(track.name)} - {artist}'

        final_file_dir = os.path.join(*[
            f for f in [
                DefaultPaths.get_download_path(),
                clean_string(playlist_name) if playlist_name else None,
                clean_string(artist_name) if artist_name else None,
                clean_string(album_name) if album_name else None,
                f'Disk {track.disc}' if album_name else None
            ] if f is not None
        ])

        if not os.path.exists(final_file_dir):
            os.makedirs(final_file_dir, exist_ok=True)

        final_file = os.path.join(final_file_dir, f'{final_filename}.mp3')
        final_file_inc = 0

        while os.path.exists(final_file):
            final_file_inc += 1
            final_file = os.path.join(final_file_dir, f'{final_filename} ({final_file_inc}).mp3')

        os.rename(temp_mp3_file, final_file)
        os.unlink(temp_file)

    console.print(
        f'Successfully downloaded '
        f'[info]{track.name}[/info]'
        f' by '
        f'[info]{"[/info], [info]".join([a.name for a in track.artists])}[/info]',
        style='white'
    )


def download_album(ctx, album_id, *, artist_name=None):
    with console.status(
        '[white]Fetching album data ...',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            album = ctx.client.albums.get(album_id)
        except SpotifyException as e:
            time.sleep(1)
            return console.error(f'Error: {e}')

    console.print(
        f'Starting download of '
        f'[info]{album.name}',
        style='white'
    )

    console.rule()

    for index, track in enumerate(ctx.client.albums.get_tracks(album_id)):
        download_track(ctx, track.id, album_name=album.name, artist_name=artist_name)

        console.rule(
            f'[info]Download progress: {index+1}/{album.tracks} tracks'
        )

    console.print(
        f'Successfully downloaded '
        f'[info]{album.name}',
        style='white'
    )


def download_playlist(ctx, playlist_id):
    with console.status(
        '[white]Fetching playlist data ...',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            playlist = ctx.client.playlists.get(playlist_id)
        except SpotifyException as e:
            time.sleep(1)
            return console.error(f'Error: {e}')

    console.print(
        f'Starting download of '
        f'[info]{playlist.name}',
        style='white'
    )

    console.rule()

    for index, track in enumerate(ctx.client.playlists.get_items(playlist_id)):
        download_track(ctx, track.id, playlist_name=playlist.name)

        console.rule(
            f'[info]Download progress: {index+1}/{playlist.items} items'
        )

    console.print(
        f'Successfully downloaded '
        f'[info]{playlist.name}',
        style='white'
    )


def download_discography(ctx, artist_id):
    with console.status(
        '[white]Fetching artist data ...',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            artist = ctx.client.artists.get(artist_id)
        except SpotifyException as e:
            time.sleep(1)
            return console.error(f'Error: {e}')

    console.print(
        f'Starting download discography of '
        f'[info]{artist.name}',
        style='white'
    )

    for index, album in enumerate(ctx.client.artists.get_albums(artist_id)):
        download_album(ctx, album.id, artist_name=artist.name)

    console.print(
        f'Successfully downloaded discography of '
        f'[info]{artist.name}',
        style='white'
    )
