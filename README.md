<div>
    <h1 align="center">Spoffline<br>Next gen spotify downloader</h1>
</div>

<br>

<h2>Requirements</h2>

- **Python** (up to 3.10)
- **FFMPEG** (can be downloaded [here](https://github.com/BtbN/FFmpeg-Builds/releases))

<h2>Installation</h2>

Install python requirements

```shell
$ pip install -r requirements.txt
```

You must config your account:

```shell
$ python -m spoffline auth [EMAIL] [PASSWORD]
```

<h2>Usage</h2>

```shell
$ python -m spoffline dl [URL]
```
*(Only music can be downloaded for now)*

<h2>Example</h2>

<img src="./.github/assets/album.gif">
<img src="./.github/assets/proof.png">

<h2>Warning: Some things have to be concidered</h2>

 - This project is not approved by Spotify.
 - The worst that can happen is that you will be banned from Spotify
 - Some track is only available in some country (example with [Re-sublimity by KOTOKO](https://open.spotify.com/track/5ZBVGPIBgqjfJmzsd0IyP7) only available in Japan)
