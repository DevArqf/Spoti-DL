import sys
import json
import os
import yt_dlp
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def download_track(track, output_dir, audio_format, audio_quality):
    search_query = f"{track['artist']} - {track['name']}"
    
    artist = track['artist'].replace('/', '_').replace('\\', '_')
    title = track['name'].replace('/', '_').replace('\\', '_')
    clean_filename = f"{artist} - {title}" if artist and artist.lower() != 'na' else title
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, f'{clean_filename}.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format,
            'preferredquality': audio_quality,
        }],
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'keepvideo': False,
        'prefer_ffmpeg': True,
        'postprocessor_args': ['-ar', '44100'],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(f"ytsearch1:{search_query}", download=True)
        return {'status': 'success', 'track': search_query}
    except Exception as e:
        return {'status': 'failed', 'track': search_query, 'error': str(e)}

def download_tracks(tracks, config):
    output_dir = config['download']['output_directory']
    audio_format = config['download']['audio_format']
    audio_quality = config['download']['audio_quality']
    max_workers = config['download']['parallel_downloads']
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(download_track, track, output_dir, audio_format, audio_quality): track
            for track in tracks
        }
        
        for future in as_completed(futures):
            track = futures[future]
            try:
                result = future.result()
                
                progress = {
                    'type': result['status'],
                    'track': result['track'],
                    'current': result['track']
                }
                
                print(json.dumps(progress), flush=True)
                
            except Exception as e:
                progress = {
                    'type': 'failed',
                    'track': f"{track['artist']} - {track['name']}",
                    'error': str(e)
                }
                print(json.dumps(progress), flush=True)

if __name__ == '__main__':
    tracks = json.loads(sys.argv[1])
    config = json.loads(sys.argv[2])
    
    download_tracks(tracks, config)