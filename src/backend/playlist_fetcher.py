import base64
import json
import re
import sys
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yt_dlp


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)


class SilentLogger:
    def debug(self, msg):
        return

    def warning(self, msg):
        return

    def error(self, msg):
        return


def simplify_fetch_error(message):
    text = str(message)
    if "Private video" in text:
        return (
            "This YouTube playlist contains a private video. Sign into a browser that has access "
            "to it, then select that browser in YouTube Cookies Browser under Settings."
        )
    if "Could not copy Chrome cookie database" in text:
        return (
            "Chrome cookies could not be read because the browser cookie database is locked. "
            "Close Chrome completely, use another browser option, or set an exported cookies.txt "
            "file in Settings."
        )
    return text


def add_youtube_auth_options(ydl_opts, config):
    download_config = (config or {}).get("download", {}) if isinstance(config, dict) else {}
    cookies_file = download_config.get("youtube_cookies_file", "").strip()
    browser = download_config.get("youtube_cookies_browser", "").strip().lower()

    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file
        return

    if browser:
        ydl_opts["cookiesfrombrowser"] = (browser,)


def fetch_url(url):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_spotify_playlist_id(playlist_url):
    if "playlist/" in playlist_url:
        return playlist_url.split("playlist/")[-1].split("?")[0]
    return playlist_url.strip()


def parse_youtube_playlist_id(playlist_url):
    match = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", playlist_url)
    return match.group(1) if match else None


def normalize_duration_seconds(duration_ms):
    if duration_ms is None:
        return 0
    return max(0, int(round(duration_ms / 1000)))


def fetch_spotify_playlist_from_api(playlist_url, client_id, client_secret):
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials

    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)

    playlist_id = parse_spotify_playlist_id(playlist_url)
    playlist_info = sp.playlist(playlist_id)
    tracks = []

    results = sp.playlist_tracks(playlist_id)
    while results:
        for item in results["items"]:
            track = item.get("track")
            if not track:
                continue

            tracks.append(
                {
                    "name": track["name"],
                    "artist": ", ".join(artist["name"] for artist in track["artists"]),
                    "artists": [artist["name"] for artist in track["artists"]],
                    "album": track["album"]["name"],
                    "duration": normalize_duration_seconds(track.get("duration_ms")),
                    "source_type": "spotify_track",
                    "source_url": track.get("external_urls", {}).get("spotify", ""),
                }
            )

        results = sp.next(results) if results.get("next") else None

    return {
        "name": playlist_info["name"],
        "tracks": tracks,
        "source_type": "spotify_playlist",
    }


def fetch_spotify_playlist_public_metadata(playlist_url):
    playlist_id = parse_spotify_playlist_id(playlist_url)
    html = fetch_url(f"https://open.spotify.com/playlist/{playlist_id}")

    state_match = re.search(
        r'<script id="initialState" type="text/plain">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not state_match:
        return None

    state = json.loads(base64.b64decode(state_match.group(1)))
    playlist_uri = f"spotify:playlist:{playlist_id}"
    playlist_data = state.get("entities", {}).get("items", {}).get(playlist_uri)
    if not playlist_data:
        return None

    track_count = playlist_data.get("content", {}).get("totalCount", 0)
    visible_tracks = len(playlist_data.get("content", {}).get("items", []))

    return {
        "name": unescape(playlist_data.get("name", "Spotify Playlist")),
        "track_count": track_count,
        "visible_tracks": visible_tracks,
    }


def fetch_spotify_playlist(playlist_url, client_id, client_secret):
    if not client_id or not client_secret:
        return {
            "error": (
                "Spotify credentials are required for Spotify playlists. "
                "For YouTube playlists, credentials are not needed."
            )
        }

    try:
        return fetch_spotify_playlist_from_api(playlist_url, client_id, client_secret)
    except Exception as exc:
        message = str(exc)
        public_info = None

        try:
            public_info = fetch_spotify_playlist_public_metadata(playlist_url)
        except Exception:
            public_info = None

        if "Active premium subscription required for the owner of the app" in message:
            playlist_name = public_info["name"] if public_info else "This Spotify playlist"
            track_hint = ""
            if public_info:
                track_hint = (
                    f" Spotify shows it as a public playlist with {public_info['track_count']} tracks, "
                    "but the Web API is blocked for your app owner account."
                )

            return {
                "error": (
                    f"{playlist_name} cannot be fetched because Spotify blocked this developer app. "
                    "The Spotify account that owns the app in the Spotify Developer Dashboard must have "
                    "an active Premium subscription for development-mode API access to work."
                    f"{track_hint}"
                )
            }

        return {"error": message}


def fetch_youtube_playlist(playlist_url, config=None):
    playlist_id = parse_youtube_playlist_id(playlist_url)
    if not playlist_id:
        return {"error": "Invalid YouTube playlist URL."}

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
        "playlistend": 5000,
        "ignoreerrors": True,
        "logger": SilentLogger(),
    }
    add_youtube_auth_options(ydl_opts, config)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    if not info or info.get("_type") != "playlist":
        return {"error": "The provided YouTube URL is not a playlist."}

    tracks = []
    for entry in info.get("entries", []):
        if not entry:
            continue

        title = entry.get("title") or "Unknown Title"
        artist = entry.get("channel") or entry.get("uploader") or "Unknown Channel"
        duration = int(entry.get("duration") or 0)
        webpage_url = entry.get("webpage_url") or f"https://www.youtube.com/watch?v={entry.get('id', '')}"

        tracks.append(
            {
                "name": title,
                "artist": artist,
                "artists": [artist],
                "album": info.get("title", ""),
                "duration": duration,
                "source_type": "youtube_video",
                "source_url": webpage_url,
            }
        )

    return {
        "name": info.get("title", "YouTube Playlist"),
        "tracks": tracks,
        "source_type": "youtube_playlist",
    }


def detect_source_type(playlist_url):
    lower_url = playlist_url.lower()
    if "youtube.com" in lower_url or "youtu.be" in lower_url:
        return "youtube"
    if "spotify.com" in lower_url or re.fullmatch(r"[A-Za-z0-9]{22}", playlist_url.strip()):
        return "spotify"
    return "unknown"


def fetch_playlist(playlist_url, client_id, client_secret, config=None):
    source_type = detect_source_type(playlist_url)

    try:
        if source_type == "youtube":
            return fetch_youtube_playlist(playlist_url, config)
        if source_type == "spotify":
            return fetch_spotify_playlist(playlist_url, client_id, client_secret)
        return {
            "error": (
                "Unsupported playlist URL. Use a Spotify playlist URL or a YouTube playlist URL."
            )
        }
    except HTTPError as exc:
        return {"error": f"HTTP error while fetching playlist: {exc}"}
    except URLError as exc:
        return {"error": f"Network error while fetching playlist: {exc}"}
    except Exception as exc:
        return {"error": simplify_fetch_error(exc)}


if __name__ == "__main__":
    playlist_url = sys.argv[1]
    client_id = sys.argv[2]
    client_secret = sys.argv[3]
    config = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}

    result = fetch_playlist(playlist_url, client_id, client_secret, config)
    print(json.dumps(result))
