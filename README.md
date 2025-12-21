# Spoti-DL

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)

This repository is a command-line tool for downloading entire Spotify playlists as high-quality MP3 files with a clean terminal interface.

---

## Creation Reason

As an automation specialist, I got tired of dealing with online playlist downloaders that cap you at 100 tracks or require premium subscriptions. Most of these services are unreliable at best, randomly skipping tracks or failing mid-download. After watching yet another sketchy download bot fail halfway through a 506-track playlist, I decided to build something better.

This tool uses the official Spotify API to fetch playlist metadata and yt-dlp to source audio from YouTube. No arbitrary limits, no subscriptions, no compromises on quality.

### What was wrong with existing solutions

Most online downloaders limit you to 100 songs per playlist and charge monthly fees for anything beyond that. The free alternatives are riddled with ads, produce low-quality 128kbps files, and frequently fail on longer playlists. None of them provide progress tracking or ETAs, so you're left staring at a loading spinner hoping it doesn't crash.

### What this does differently

This tool downloads unlimited tracks at 320kbps, shows real-time progress with ETAs, and runs entirely on your local machine. It's open source, auditable, and uses official APIs rather than sketchy web scrapers. If a download fails, you get a clean report of what went wrong instead of silent failures.

---

## Features

The interface uses Rich for terminal formatting, giving you color-coded progress indicators, real-time download bars, and ETA calculations. You can download entire playlists without track limits, and all files are encoded at 320kbps MP3 with proper metadata tagging.

The tool handles errors gracefully, tracking which downloads succeed and which fail. Failed tracks get listed at the end so you can investigate or retry them manually. Everything runs locally using the official Spotify API, so there's no risk of account compromise or data being sent to third parties.

---

## Installation

You'll need Python 3.8 or higher and FFmpeg for audio conversion. On Windows, grab FFmpeg from https://ffmpeg.org/ or install it with winget by running `winget install -e --id Gyan.FFmpeg` in powershell. Mac users can install it with `brew install ffmpeg`. Linux users can use their package manager, typically `sudo apt install ffmpeg`.

Start by cloning this repository and installing the Python dependencies:

```bash
git clone https://github.com/DevArqf/spoti-dl
cd spoti-dl
pip install -r requirements.txt
```

Next, you need to create a Spotify API application. Head to the [Spotify Developer Page](https://developer.spotify.com/) and log in. Create a new app with whatever name you want. The important part is adding `http://127.0.0.1:9090` as a redirect URI.

Once your app is created, copy the Client ID and Client Secret.

---

## Usage

Run the script with `python spotify_downloader.py`. On first launch, you'll go through an interactive setup wizard that configures your API credentials, download preferences, audio quality, and parallel download settings. After setup, a browser window will open asking you to authorize the app. After logging in, you'll be redirected to a blank page. Copy the entire URL from your browser's address bar and paste it into the terminal.

The main menu gives you options to download a playlist or configure settings. When you choose to download, enter your Spotify playlist URL. You can get this by right-clicking any playlist in Spotify and selecting "Copy Playlist Link". The tool will fetch all tracks, display a preview table, and ask for confirmation before starting the download.

All tracks get saved to your configured output directory (default is `spotify_downloads`). You'll see real-time progress bars with ETAs as each track downloads in parallel. At the end, you get a summary showing successful, skipped, and failed downloads.

Here's what a typical session looks like:

```
    ███████╗██████╗  ██████╗ ████████╗██╗      ██████╗ ██╗     
    ██╔════╝██╔══██╗██╔═══██╗╚══██╔══╝██║      ██╔══██╗██║     
    ███████╗██████╔╝██║   ██║   ██║   ██║█████╗██║  ██║██║     
    ╚════██║██╔═══╝ ██║   ██║   ██║   ██║╚════╝██║  ██║██║     
    ███████║██║     ╚██████╔╝   ██║   ██║      ██████╔╝███████╗
    ╚══════╝╚═╝      ╚═════╝    ╚═╝   ╚═╝      ╚═════╝ ╚══════╝

✓ Successfully authenticated with Spotify!

Enter your Spotify playlist URL or ID: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M

✓ Found 150 tracks in playlist!

📀 Your Playlist
┌────┬──────────────────────────┬─────────────────┬──────────┐
│ #  │ Track                    │ Artist          │ Duration │
├────┼──────────────────────────┼─────────────────┼──────────┤
│ 1  │ Song Name               	│ Artist Name     │ 3:45     │
└────┴──────────────────────────┴─────────────────┴──────────┘

Start downloading? [y/n] (y): y

Downloading playlist... ━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
```

---

## Configuration

The tool uses a `config.json` file to store all your settings. On first run, an interactive wizard helps you set everything up. You can modify settings anytime through the configuration menu.

Available settings include output directory, audio format (MP3, FLAC, M4A, Opus, WAV), audio quality (128-320kbps), number of parallel downloads (1-10), whether to skip already downloaded files, and whether to show the preview table.

You can access the configuration menu from the main menu by selecting option 2. Changes are saved to `config.json` and persist between sessions.

Example configuration:

```json
{
    "spotify": {
        "client_id": "your_client_id",
        "client_secret": "your_client_secret",
        "redirect_uri": "http://127.0.0.1:9090"
    },
    "download": {
        "output_directory": "spotify_downloads",
        "audio_format": "mp3",
        "audio_quality": "320",
        "parallel_downloads": 5,
        "skip_existing": true
    },
    "display": {
        "show_preview": true,
        "preview_count": 10
    }
}
```

---

## Troubleshooting

If you see "Module not found" errors, make sure you've installed all dependencies:

```bash
pip install spotipy yt-dlp rich
```

FFmpeg errors usually mean it's not installed or not in your system PATH. Verify the installation with `ffmpeg -version`.

Authentication failures typically come from incorrect Client ID/Secret or a mismatched redirect URI. Double check that you've added `http://127.0.0.1:9090` exactly in your Spotify app settings. If credentials are wrong, you can reconfigure them through the settings menu or by running the setup wizard again.

Some tracks will inevitably fail to download if they're not available on YouTube or are region-restricted. The tool lists these at the end so you know what's missing.

> [!NOTE]
> If you hit rate limits, YouTube is temporarily throttling your requests. Wait a few minutes before retrying. **DO NOT WORRY**! If you run the python script again, it will recognise already downloaded files.

---

## Contact

**Malik Johnson**

Website: [malikjohnson.info](https://malikjohnson.info)  
LinkedIn: [malik-johnson-597700397](https://www.linkedin.com/in/malik-johnson-597700397)    
Discord: [@arqf](https://discord.com/users/899385550585364481)

---

## License

MIT License. Use this project however you want.

---

<div align="center">

☕ Made by [Malik Johnson](https://github.com/DevArqf) ☕

</div>