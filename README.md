# Spoti-DL Desktop App

A beautiful, modern desktop application for downloading Spotify playlists built with Electron and Python.

## Features

- **Beautiful UI**: Dark theme with glassmorphism effects and smooth animations
- **Real-time Progress**: Track download progress with live statistics
- **Playlist Preview**: See tracks before downloading
- **Configurable Settings**: Customize audio format, quality, and parallel downloads
- **Cross-platform**: Works on Windows, macOS, and Linux

## Prerequisites

1. **Node.js** (v16 or higher)
2. **Python 3.8+**
3. **FFmpeg** installed and in your system PATH
4. **Spotify Developer Credentials** (Client ID and Secret)

### Installing FFmpeg

**Windows:**

```bash
winget install -e --id Gyan.FFmpeg
```

**macOS:**

```bash
brew install ffmpeg
```

**Linux:**

```bash
sudo apt install ffmpeg
```

## Installation

### 1. Install Python Dependencies

```bash
pip install spotipy yt-dlp
```

### 2. Install Node Dependencies

Navigate to the project directory and install Node packages:

```bash
npm install
```

### 3. Get Spotify API Credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Copy your Client ID and Client Secret
4. You'll enter these in the app's Settings

## Running the App

### Development Mode

```bash
npm start
```

## Building the App

### Build for Current Platform

```bash
npm run build
```

### Build for Specific Platforms

**Windows:**

```bash
npm run build:win
```

**macOS:**

```bash
npm run build:mac
```

**Linux:**

```bash
npm run build:linux
```

The built applications will be in the `dist` folder.

## Usage Guide

### First Time Setup

1. Launch the application
2. Click on **Settings** in the sidebar
3. Enter your Spotify **Client ID** and **Client Secret**
4. Select an **Output Directory** where downloads will be saved
5. Configure audio preferences (format, quality, parallel downloads)
6. Click **Save Settings**

### Downloading a Playlist

1. Go to **Download** view
2. Paste a Spotify playlist URL
3. Click **Fetch Playlist**
4. Preview the tracks
5. Click **Download All**
6. Monitor progress in real-time

### Settings Options

- **Audio Format**: Choose between MP3, FLAC, M4A, Opus, or WAV
- **Audio Quality**: 128, 192, 256, or 320 kbps (for MP3/M4A)
- **Parallel Downloads**: 1-10 simultaneous downloads (5 recommended)

## Troubleshooting

### "FFmpeg not found"

Make sure FFmpeg is installed and accessible from your terminal:

```bash
ffmpeg -version
```

If not found, add FFmpeg to your system PATH.

### "Failed to fetch playlist"

- Check your Spotify credentials in Settings
- Ensure the playlist URL is correct
- Verify internet connection

### Downloads failing

- Some tracks may not be available on YouTube
- Check your internet connection
- Try reducing parallel downloads if experiencing timeouts

### Build errors

If you encounter build errors:

```bash
# Clean node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Electron cache
npm cache clean --force
```

---

**Made with ❤️ by DevArqf**
