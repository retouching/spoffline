import click
from librespot.core import Session

from spoffline.configuration import Configuration
from spoffline.console import console
from spoffline.spotify.client import Client


@click.command()
@click.argument('email')
@click.argument('password')
def cli(email, password):
    """Create auth configuration"""

    client = Client(email, password)

    with console.status(
        '[white]Connect to account ...',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            client.session.get_api_session()
        except Session.SpotifyAuthenticationException as e:
            return console.error(f'Error: Spotify return bad response ({e})')

    Configuration.create(email, password)

    console.print('[white]Successfully saved configuration!')
