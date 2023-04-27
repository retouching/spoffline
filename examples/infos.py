from spoffline.spotify.client import Client


EMAIL = 'xxx@xxx.com'
PASSWORD = 'xxx'
ARTIST_URL = 'xxx'


def main():
    """
    Get informations on the spotify API
    """

    # Create client
    client = Client(email=EMAIL, password=PASSWORD, cache_path='./cache')

    # Get artist id (function return tuple with url id and url type)
    artist_id, _ = Client.parse_url(ARTIST_URL)

    # Get artist informations
    artist = client.artists.get(artist_id)

    print(f'Artist: {artist.name} [ID: {artist.id}]')

    # Get an album (Warning: get as list can take a long time if artist have a lost of albums)
    album = next(client.artists.get_albums(artist.id), None)

    print(f'Album: {album.name} ({album.tracks} tracks) [ID: {album.id}]')

    # Get a track (Warning: get as list can take a long time if album have a lost of tracks)
    track = next(client.albums.get_tracks(album.id), None)

    print(f'Track: {track.name} [ID: {track.id}] [PlayableID: {track.playable_id}]')

    # Get all available fields on models (spoffline/models)


if __name__ == '__main__':
    main()
