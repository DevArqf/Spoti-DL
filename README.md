# Playlist Audio Downloader

Desktop app for downloading Spotify, YouTube, and SoundCloud playlists or liked tracks as high-quality audio files with Electron and Python.

## Features

- Download Spotify playlists, YouTube playlists, SoundCloud playlists, and SoundCloud liked tracks from one app
- Preview playlist or collection name, source, track count, and total duration before downloading
- Use smarter YouTube matching for Spotify tracks with title, artist, album, and duration scoring
- Download YouTube and SoundCloud direct-source tracks without forcing a Spotify-style rematch flow
- Skip tracks that already exist in the output folder instead of downloading duplicates
- Configure browser-based authentication or an exported `cookies.txt` file for restricted YouTube videos and signed-in SoundCloud likes pages
- Retry and back off automatically when direct-source downloads hit temporary rate limits
- Monitor live progress with success, skipped, failed, and remaining counts
- Build installers for Windows, macOS, Linux, and a portable Windows build

## Prerequisites

1. `Node.js` 16 or higher
2. `Python` 3.8 or higher
3. `FFmpeg` installed and available in `PATH`
4. Spotify Developer credentials only if you want to fetch Spotify playlists

You do not need Spotify credentials for YouTube or SoundCloud collections.

### Installing FFmpeg

**Windows**

```bash
winget install -e --id Gyan.FFmpeg
```

**macOS**

```bash
brew install ffmpeg
```

**Linux**

```bash
sudo apt install ffmpeg
```

## Installation

### 1. Install Python Dependencies

```bash
pip install spotipy yt-dlp rich
```

### 2. Install Node Dependencies

```bash
npm install
```

### 3. Get Spotify API Credentials

Only required for Spotify playlists.

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Copy your Client ID and Client Secret
4. Enter them in the app settings

## Running the App

### Development Mode

```bash
npm start
```

## Usage Guide

### First Time Setup

1. Launch the application.
2. Open **Settings**.
3. If you plan to use Spotify playlists, enter your Spotify **Client ID** and **Client Secret**.
4. Choose an **Output Directory**.
5. Select an **Audio Format**, **Audio Quality**, and **Parallel Downloads** value.
6. Optional: set **Cookies Browser** to `chrome`, `edge`, `firefox`, or `brave` if you need access to private or restricted YouTube content or signed-in SoundCloud likes pages.
7. Optional: set **Cookies File** to an exported Netscape-format `cookies.txt` file. When this is set, it is preferred over browser cookie extraction.
8. Save settings.

### Supported Collection URLs

- Spotify playlist URLs such as `https://open.spotify.com/playlist/...`
- YouTube playlist URLs such as `https://www.youtube.com/playlist?list=...`
- SoundCloud playlist URLs such as `https://soundcloud.com/.../sets/...`
- SoundCloud likes URLs such as `https://soundcloud.com/.../likes`
- Signed-in SoundCloud likes alias URLs such as `https://soundcloud.com/you/likes`

### Downloading a Playlist or Collection

1. Open **Download**.
2. Paste a supported Spotify, YouTube, or SoundCloud URL.
3. Click **Fetch Playlist**.
4. Review the preview.
5. Click **Download All**.
6. Watch the live progress panel for completed, skipped, and failed tracks.

### Notes on Download Behavior

- Spotify playlists are fetched from Spotify, then matched against YouTube search results before downloading.
- YouTube playlists download directly from the playlist entries that were fetched.
- SoundCloud playlists and liked tracks download directly from the fetched SoundCloud track URLs.
- Existing audio files in the output directory are skipped automatically.
- Some unavailable or private YouTube videos are reported as skipped instead of failing the entire batch.
- Direct-source SoundCloud downloads automatically reduce concurrency and retry after temporary `429 Too Many Requests` responses.

## Troubleshooting

### "Please configure Spotify credentials"

Spotify credentials are required for Spotify playlists only. They are not required for YouTube or SoundCloud collections.

### Spotify premium-related API error

If Spotify reports that an active Premium subscription is required for the app owner, the app will not be able to fetch Spotify playlist tracks through that developer app until the Spotify account that owns the app has Premium.

### Private or restricted YouTube videos

- Sign into a supported browser that has access to the video and select that browser in settings.
- If browser cookie extraction fails, close the browser completely and try again.
- If needed, export a Netscape-format `cookies.txt` file and set it in the app.
- If YouTube asks you to confirm your age or verify you are not a bot, use a fresher signed-in `cookies.txt` export from a browser where the content already opens normally.

### SoundCloud likes pages are not public

- `https://soundcloud.com/you/likes` requires a signed-in session.
- Use **Cookies Browser** or **Cookies File** so the app can resolve your actual SoundCloud account and fetch liked tracks through the authenticated API.
- If the app still cannot read the page, re-export the cookies file from the browser where your SoundCloud likes page is currently working.

### `HTTP Error 429: Too Many Requests`

- The source site temporarily rate-limited requests.
- The app now retries automatically for direct-source downloads, but very large SoundCloud collections may still need a pause before retrying.
- Reduce **Parallel Downloads** if you continue seeing rate-limit failures.

### "FFmpeg not found"

Verify FFmpeg is available:

```bash
ffmpeg -version
```

If the command fails, install FFmpeg and add it to your system `PATH`.

### Tracks are being skipped

Tracks can be skipped when:

- the file already exists in the output directory
- the YouTube video is private or unavailable
- YouTube does not expose a usable downloadable format for that track
