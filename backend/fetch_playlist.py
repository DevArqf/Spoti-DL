import sys
import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

def fetch_playlist(playlist_url, client_id, client_secret):
    try:
        auth_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        if 'playlist/' in playlist_url:
            playlist_id = playlist_url.split('playlist/')[-1].split('?')[0]
        else:
            playlist_id = playlist_url
        
        playlist_info = sp.playlist(playlist_id)
        tracks = []
        
        results = sp.playlist_tracks(playlist_id)
        while results:
            for item in results['items']:
                track = item['track']
                if track:
                    tracks.append({
                        'name': track['name'],
                        'artist': ', '.join([artist['name'] for artist in track['artists']]),
                        'album': track['album']['name'],
                        'duration': track['duration_ms']
                    })
            
            results = sp.next(results) if results['next'] else None
        
        return {
            'name': playlist_info['name'],
            'tracks': tracks
        }
        
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    playlist_url = sys.argv[1]
    client_id = sys.argv[2]
    client_secret = sys.argv[3]
    
    result = fetch_playlist(playlist_url, client_id, client_secret)
    print(json.dumps(result))