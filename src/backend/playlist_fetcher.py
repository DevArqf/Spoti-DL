import base64
import http.cookiejar
import json
import os
import re
import sys
from html import unescape
from urllib.parse import urlencode
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
            "to it, then select that browser in Cookies Browser under Settings."
        )
    if "confirm you're not a bot" in text.lower():
        return (
            "YouTube asked for an anti-bot verification. Try a fresher cookies.txt export "
            "from the browser where YouTube is already working."
        )
    if "sign in to confirm your age" in text.lower():
        return (
            "This YouTube content is age-restricted. Use a signed-in browser session or a cookies.txt file "
            "from a YouTube account that can open it."
        )
    if "Could not copy Chrome cookie database" in text:
        return (
            "Chrome cookies could not be read because the browser cookie database is locked. "
            "Close Chrome completely, use another browser option, or set an exported cookies.txt "
            "file in Settings."
        )
    if "soundcloud.com/you/likes" in text or "login required" in text.lower():
        return (
            "This SoundCloud likes page needs your signed-in browser session. "
            "Choose your browser under Cookies Browser in Settings, or set a cookies.txt file."
        )
    return text


def add_browser_auth_options(ydl_opts, config):
    download_config = (config or {}).get("download", {}) if isinstance(config, dict) else {}
    cookies_file = download_config.get("youtube_cookies_file", "").strip()
    browser = download_config.get("youtube_cookies_browser", "").strip().lower()

    if cookies_file:
        if not os.path.exists(cookies_file):
            raise FileNotFoundError(f"Cookies file not found: {cookies_file}")
        ydl_opts["cookiefile"] = cookies_file
        return

    if browser:
        ydl_opts["cookiesfrombrowser"] = (browser,)


def fetch_url(url):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json(url, headers=None, query=None):
    resolved_url = url
    if query:
        resolved_url = f"{url}?{urlencode(query)}"

    request = Request(resolved_url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def parse_spotify_playlist_id(playlist_url):
    if "playlist/" in playlist_url:
        return playlist_url.split("playlist/")[-1].split("?")[0]
    return playlist_url.strip()


def parse_youtube_playlist_id(playlist_url):
    match = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", playlist_url)
    return match.group(1) if match else None


def extract_soundcloud_oauth_token(config):
    download_config = (config or {}).get("download", {}) if isinstance(config, dict) else {}
    cookies_file = download_config.get("youtube_cookies_file", "").strip()

    if not cookies_file:
        return None

    try:
        cookie_jar = http.cookiejar.MozillaCookieJar(cookies_file)
        cookie_jar.load(ignore_discard=True, ignore_expires=True)
    except Exception:
        return None

    for cookie in cookie_jar:
        if cookie.name == "oauth_token" and cookie.value:
            return cookie.value

    return None


def extract_soundcloud_client_id():
    homepage = fetch_url("https://soundcloud.com/")
    script_urls = re.findall(r'<script[^>]+src="([^"]+)"', homepage)

    for script_url in reversed(script_urls):
        try:
            script_body = fetch_url(script_url)
        except Exception:
            continue

        match = re.search(r'client_id\s*:\s*"([0-9a-zA-Z]{32})"', script_body)
        if match:
            return match.group(1)

    return None


def resolve_soundcloud_likes_url(playlist_url, config=None):
    if "/you/likes" not in playlist_url.lower():
        return playlist_url

    oauth_token = extract_soundcloud_oauth_token(config)
    if not oauth_token:
        raise ValueError(
            "This SoundCloud likes page needs a cookies.txt file or browser session with a valid SoundCloud login."
        )

    client_id = extract_soundcloud_client_id()
    if not client_id:
        raise ValueError("Could not determine the SoundCloud client id needed to resolve your likes page.")

    current_user = fetch_json(
        "https://api-v2.soundcloud.com/me",
        headers={"Authorization": f"OAuth {oauth_token}"},
        query={"client_id": client_id},
    )

    permalink = current_user.get("permalink")
    if not permalink:
        raise ValueError("Could not resolve your SoundCloud profile from the current login session.")

    return f"https://soundcloud.com/{permalink}/likes"


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
    add_browser_auth_options(ydl_opts, config)

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


def build_soundcloud_track(entry, collection_title):
    title = entry.get("title") or "Unknown Title"
    artist = entry.get("artist") or entry.get("uploader") or entry.get("channel") or "Unknown Artist"
    duration = int(entry.get("duration") or 0)
    webpage_url = entry.get("webpage_url") or entry.get("original_url") or ""

    return {
        "name": title,
        "artist": artist,
        "artists": [artist],
        "album": collection_title or "",
        "duration": duration,
        "source_type": "soundcloud_track",
        "source_url": webpage_url,
    }


def build_soundcloud_track_from_api(track, collection_title):
    title = track.get("title") or "Unknown Title"
    artist = (
        track.get("user", {}).get("username")
        or track.get("publisher_metadata", {}).get("artist")
        or "Unknown Artist"
    )
    duration = normalize_duration_seconds(track.get("duration"))
    webpage_url = track.get("permalink_url") or ""

    return {
        "name": title,
        "artist": artist,
        "artists": [artist],
        "album": collection_title or "",
        "duration": duration,
        "source_type": "soundcloud_track",
        "source_url": webpage_url,
    }


def fetch_soundcloud_collection(playlist_url, config=None):
    if "/likes" in playlist_url.lower():
        return fetch_soundcloud_likes_collection(playlist_url, config)

    resolved_url = resolve_soundcloud_likes_url(playlist_url, config)
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
        "playlistend": 5000,
        "ignoreerrors": True,
        "logger": SilentLogger(),
    }
    add_browser_auth_options(ydl_opts, config)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(resolved_url, download=False)

    if not info:
        return {"error": "The provided SoundCloud URL could not be read."}

    entries = info.get("entries") or []
    if not entries:
        return {"error": "No playable tracks were found in this SoundCloud collection."}

    collection_title = info.get("title") or "SoundCloud Collection"
    tracks = [build_soundcloud_track(entry, collection_title) for entry in entries if entry]

    if not tracks:
        return {"error": "No usable tracks were found in this SoundCloud collection."}

    lower_url = playlist_url.lower()
    collection_type = "soundcloud_likes" if "/likes" in lower_url else "soundcloud_playlist"
    fallback_name = "SoundCloud Likes" if collection_type == "soundcloud_likes" else "SoundCloud Playlist"

    return {
        "name": collection_title or fallback_name,
        "tracks": tracks,
        "source_type": collection_type,
    }


def resolve_soundcloud_user_for_likes(playlist_url, config=None):
    client_id = extract_soundcloud_client_id()
    if not client_id:
        raise ValueError("Could not determine the SoundCloud client id needed to resolve this likes page.")

    if "/you/likes" in playlist_url.lower():
        oauth_token = extract_soundcloud_oauth_token(config)
        if not oauth_token:
            raise ValueError(
                "This SoundCloud likes page needs a cookies.txt file or browser session with a valid SoundCloud login."
            )

        current_user = fetch_json(
            "https://api-v2.soundcloud.com/me",
            headers={"Authorization": f"OAuth {oauth_token}"},
            query={"client_id": client_id},
        )
        return current_user, client_id, oauth_token

    public_profile_url = playlist_url.rsplit("/likes", 1)[0]
    resolved_user = fetch_json(
        "https://api-v2.soundcloud.com/resolve",
        query={"url": public_profile_url, "client_id": client_id},
    )
    return resolved_user, client_id, None


def fetch_soundcloud_likes_collection(playlist_url, config=None):
    user, client_id, oauth_token = resolve_soundcloud_user_for_likes(playlist_url, config)
    user_id = user.get("id")
    if not user_id:
        return {"error": "Could not resolve the SoundCloud user for this likes page."}

    collection_name = f"{user.get('username') or user.get('permalink') or 'SoundCloud'} Likes"
    headers = {"Authorization": f"OAuth {oauth_token}"} if oauth_token else None
    query = {
        "client_id": client_id,
        "limit": 200,
        "linked_partitioning": "1",
    }
    next_url = f"https://api-v2.soundcloud.com/users/{user_id}/likes"
    tracks = []

    while next_url and len(tracks) < 5000:
        page = fetch_json(next_url, headers=headers, query=query)
        for item in page.get("collection", []):
            track = item.get("track")
            if not track:
                continue
            tracks.append(build_soundcloud_track_from_api(track, collection_name))
            if len(tracks) >= 5000:
                break

        next_url = page.get("next_href")
        query = None

    if not tracks:
        return {"error": "No playable liked tracks were found for this SoundCloud account."}

    return {
        "name": collection_name,
        "tracks": tracks,
        "source_type": "soundcloud_likes",
    }


def detect_source_type(playlist_url):
    lower_url = playlist_url.lower()
    if "youtube.com" in lower_url or "youtu.be" in lower_url:
        return "youtube"
    if "soundcloud.com" in lower_url:
        return "soundcloud"
    if "spotify.com" in lower_url or re.fullmatch(r"[A-Za-z0-9]{22}", playlist_url.strip()):
        return "spotify"
    return "unknown"


def fetch_playlist(playlist_url, client_id, client_secret, config=None):
    source_type = detect_source_type(playlist_url)

    try:
        if source_type == "youtube":
            return fetch_youtube_playlist(playlist_url, config)
        if source_type == "soundcloud":
            return fetch_soundcloud_collection(playlist_url, config)
        if source_type == "spotify":
            return fetch_spotify_playlist(playlist_url, client_id, client_secret)
        return {
            "error": (
                "Unsupported playlist URL. Use a Spotify, YouTube, or SoundCloud playlist URL."
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
