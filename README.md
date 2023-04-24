<center>
<h1>Spoffline</h1>
<h3>Next gen spotify downloader</h3>
</center>

---

<h2>Requirements</h2>

- **Python** (up to 3.10)
- **FFMPEG** (can be downloaded [here](https://github.com/BtbN/FFmpeg-Builds/releases))

<h2>Installation</h2>

Install python requirements

```shell
$ pip install -r requirements.txt
```

You must config your account in the config.yml file:

```yaml
credentials:
    client_id: xxx
    client_secret: xxx
    email: xxx@xxx.xxx
    password: xxx
```

ClientId and ClientSecret can be created [here](https://developer.spotify.com/dashboard/create)

<h2>Usage</h2>

```shell
$ python -m spoffline dl [URL]
```
*(Only track and album available for download for now)*

<h2>Example</h2>

<img src="./.github/assets/album.gif">
<img src="./.github/assets/proof.png">
