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

<h2>TODO List</h2>

- [x] Add support for playlist
- [x] Add support for artist albums
- [x] Add api support (to embed it in other projects)
- [ ] Add example usage of api
