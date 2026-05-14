import json
import os
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yt_dlp


NEGATIVE_KEYWORDS = {
    "karaoke",
    "nightcore",
    "slowed",
    "reverb",
    "sped up",
    "8d",
    "instrumental",
    "cover",
    "fan made",
}

POSITIVE_KEYWORDS = {
    "official",
    "audio",
    "topic",
    "provided to youtube",
    "music video",
}

MAX_SEARCH_RESULTS = 10
MIN_CONFIDENCE_SCORE = 55
AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".opus", ".wav", ".aac", ".ogg"}
FORMAT_FALLBACKS = [
    "bestaudio/best",
    "bestaudio*",
    "bestaudio",
    "best",
]


class SilentLogger:
    def debug(self, msg):
        return

    def warning(self, msg):
        return

    def error(self, msg):
        return


def normalize_text(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def tokenize(value):
    return [token for token in normalize_text(value).split() if token]


def safe_filename(track):
    artist = (track.get("artist") or "").replace("/", "_").replace("\\", "_")
    title = (track.get("name") or "Unknown Title").replace("/", "_").replace("\\", "_")
    return f"{artist} - {title}" if artist else title


def track_identity_key(track):
    return normalize_text(safe_filename(track))


def scan_existing_track_keys(output_dir):
    existing = set()

    for path in Path(output_dir).iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue

        existing.add(normalize_text(path.stem))

    return existing


def build_download_options(output_dir, filename, audio_format, audio_quality):
    return {
        "format": FORMAT_FALLBACKS[0],
        "outtmpl": os.path.join(output_dir, f"{filename}.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": audio_quality,
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "keepvideo": False,
        "prefer_ffmpeg": True,
        "postprocessor_args": ["-ar", "44100"],
        "logger": SilentLogger(),
    }


def add_youtube_cookies_option(ydl_opts, config):
    download_config = config.get("download", {}) if isinstance(config, dict) else {}
    cookies_file = download_config.get("youtube_cookies_file", "").strip()
    browser = download_config.get("youtube_cookies_browser", "").strip().lower()

    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file
        return

    if browser:
        ydl_opts["cookiesfrombrowser"] = (browser,)


def simplify_download_error(message):
    text = str(message)
    if "Private video" in text:
        return (
            "Private YouTube video. Sign into the selected browser with access to this video, "
            "then enable that browser under YouTube Cookies Browser in Settings."
        )
    if "Could not copy Chrome cookie database" in text:
        return (
            "Chrome cookies could not be read because the browser cookie database is locked. "
            "Close Chrome completely, choose another browser, or set an exported cookies.txt file in Settings."
        )
    if "Requested format is not available" in text:
        return (
            "YouTube did not expose the preferred audio-only format for this video, "
            "and all fallback format attempts failed."
        )
    return text


def is_skippable_download_error(message):
    text = str(message)
    skip_markers = [
        "Requested format is not available",
        "Private video",
        "Video unavailable",
        "This video is unavailable",
        "Sign in if you've been granted access to this video",
        "This content isn't available",
        "The uploader has not made this video available",
    ]
    return any(marker in text for marker in skip_markers)


def overlap_score(expected_tokens, candidate_text):
    if not expected_tokens:
        return 0

    candidate_tokens = set(tokenize(candidate_text))
    matched = sum(1 for token in expected_tokens if token in candidate_tokens)
    return int((matched / len(expected_tokens)) * 100)


def keyword_penalty(track_name, candidate_blob):
    normalized_track_name = normalize_text(track_name)
    normalized_candidate = normalize_text(candidate_blob)

    penalty = 0
    for keyword in NEGATIVE_KEYWORDS:
        if keyword in normalized_candidate and keyword not in normalized_track_name:
            penalty += 18
    return penalty


def keyword_bonus(candidate_blob):
    normalized_candidate = normalize_text(candidate_blob)
    bonus = 0
    for keyword in POSITIVE_KEYWORDS:
        if keyword in normalized_candidate:
            bonus += 6
    return bonus


def duration_score(expected_duration, candidate_duration):
    if not expected_duration or not candidate_duration:
        return 0

    delta = abs(int(expected_duration) - int(candidate_duration))
    if delta <= 2:
        return 20
    if delta <= 5:
        return 16
    if delta <= 10:
        return 10
    if delta <= 20:
        return 4
    return -12


def score_candidate(track, candidate):
    title = candidate.get("title") or ""
    uploader = candidate.get("channel") or candidate.get("uploader") or ""
    description = candidate.get("description") or ""
    blob = " ".join(part for part in [title, uploader, description] if part)

    title_tokens = tokenize(track.get("name"))
    artist_tokens = tokenize(" ".join(track.get("artists") or [track.get("artist", "")]))
    album_tokens = tokenize(track.get("album"))

    score = 0
    score += overlap_score(title_tokens, title) * 0.45
    score += overlap_score(artist_tokens, blob) * 0.40
    score += overlap_score(album_tokens, blob) * 0.15
    score += duration_score(track.get("duration"), candidate.get("duration"))
    score += keyword_bonus(blob)
    score -= keyword_penalty(track.get("name", ""), blob)

    if normalize_text(track.get("name")) == normalize_text(title):
        score += 18

    return round(score, 2)


def choose_best_youtube_match(track):
    query_parts = [track.get("artist", ""), track.get("name", ""), track.get("album", "")]
    search_query = " ".join(part for part in query_parts if part).strip()

    search_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "ignoreerrors": True,
        "logger": SilentLogger(),
    }

    with yt_dlp.YoutubeDL(search_opts) as ydl:
        results = ydl.extract_info(f"ytsearch{MAX_SEARCH_RESULTS}:{search_query}", download=False)

    entries = results.get("entries", []) if results else []
    if not entries:
        return None, "No YouTube search results found."

    scored = []
    for entry in entries:
        if not entry:
            continue
        scored.append((score_candidate(track, entry), entry))

    if not scored:
        return None, "No usable YouTube candidates found."

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_candidate = scored[0]

    if best_score < MIN_CONFIDENCE_SCORE:
        return None, (
            f"Best match score {best_score} was below the confidence threshold for "
            f"{track.get('artist', 'Unknown Artist')} - {track.get('name', 'Unknown Title')}."
        )

    return best_candidate, None


def download_from_url(source_url, track, output_dir, audio_format, audio_quality):
    filename = safe_filename(track)
    last_error = None

    for format_selector in FORMAT_FALLBACKS:
        ydl_opts = build_download_options(output_dir, filename, audio_format, audio_quality)
        ydl_opts["format"] = format_selector
        add_youtube_cookies_option(
            ydl_opts,
            {
                "download": {
                    "youtube_cookies_browser": track.get("_youtube_cookies_browser", ""),
                    "youtube_cookies_file": track.get("_youtube_cookies_file", ""),
                }
            },
        )

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(source_url, download=True)
            return
        except Exception as exc:
            last_error = exc
            if "Requested format is not available" not in str(exc):
                raise

    if last_error:
        raise last_error


def download_track(track, output_dir, audio_format, audio_quality):
    try:
        source_type = track.get("source_type")

        if source_type == "youtube_video":
            download_from_url(track["source_url"], track, output_dir, audio_format, audio_quality)
            return {
                "status": "success",
                "track": f"{track.get('artist', 'Unknown Artist')} - {track.get('name', 'Unknown Title')}",
                "current": f"{track.get('artist', 'Unknown Artist')} - {track.get('name', 'Unknown Title')}",
            }

        best_candidate, error = choose_best_youtube_match(track)
        if error:
            return {
                "status": "failed",
                "track": f"{track.get('artist', 'Unknown Artist')} - {track.get('name', 'Unknown Title')}",
                "error": error,
            }

        candidate_url = best_candidate.get("webpage_url")
        if not candidate_url and best_candidate.get("id"):
            candidate_url = f"https://www.youtube.com/watch?v={best_candidate['id']}"

        if not candidate_url:
            return {
                "status": "failed",
                "track": f"{track.get('artist', 'Unknown Artist')} - {track.get('name', 'Unknown Title')}",
                "error": "Best YouTube match did not include a playable URL.",
            }

        download_from_url(candidate_url, track, output_dir, audio_format, audio_quality)
        return {
            "status": "success",
            "track": f"{track.get('artist', 'Unknown Artist')} - {track.get('name', 'Unknown Title')}",
            "current": f"{track.get('artist', 'Unknown Artist')} - {track.get('name', 'Unknown Title')}",
        }
    except Exception as exc:
        status = "skipped" if is_skippable_download_error(exc) else "failed"
        return {
            "status": status,
            "track": f"{track.get('artist', 'Unknown Artist')} - {track.get('name', 'Unknown Title')}",
            "error": simplify_download_error(exc),
        }


def download_tracks(tracks, config):
    output_dir = config["download"]["output_directory"]
    audio_format = config["download"]["audio_format"]
    audio_quality = config["download"]["audio_quality"]
    max_workers = config["download"]["parallel_downloads"]

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    had_failures = False
    existing_track_keys = scan_existing_track_keys(output_dir)
    scheduled_track_keys = set()
    queued_tracks = []

    for track in tracks:
        track["_youtube_cookies_browser"] = config["download"].get("youtube_cookies_browser", "")
        track["_youtube_cookies_file"] = config["download"].get("youtube_cookies_file", "")
        identity_key = track_identity_key(track)
        label = f"{track.get('artist', 'Unknown Artist')} - {track.get('name', 'Unknown Title')}"

        if identity_key in existing_track_keys or identity_key in scheduled_track_keys:
            progress = {
                "type": "skipped",
                "track": label,
                "current": label,
                "error": "Already exists in the output directory.",
            }
            print(json.dumps(progress), flush=True)
            continue

        scheduled_track_keys.add(identity_key)
        queued_tracks.append(track)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(download_track, track, output_dir, audio_format, audio_quality): track
            for track in queued_tracks
        }

        for future in as_completed(futures):
            track = futures[future]
            try:
                result = future.result()
                progress = {
                    "type": result["status"],
                    "track": result["track"],
                    "current": result.get("current", result["track"]),
                    "error": result.get("error"),
                }
                if result["status"] == "failed":
                    had_failures = True
                print(json.dumps(progress), flush=True)
            except Exception as exc:
                had_failures = True
                progress = {
                    "type": "failed",
                    "track": f"{track.get('artist', 'Unknown Artist')} - {track.get('name', 'Unknown Title')}",
                    "error": str(exc),
                }
                print(json.dumps(progress), flush=True)

    return not had_failures


if __name__ == "__main__":
    tracks = json.loads(sys.argv[1])
    config = json.loads(sys.argv[2])

    success = download_tracks(tracks, config)
    sys.exit(0 if success else 1)
