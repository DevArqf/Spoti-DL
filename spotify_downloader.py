import spotipy
from spotipy.oauth2 import SpotifyOAuth
import yt_dlp
import os
import time
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

from config_manager import (
    load_config, 
    save_config, 
    setup_wizard, 
    show_config_menu, 
    config_exists, 
    validate_config
)

console = Console()

def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def print_banner():
    banner = """
███████╗██████╗  ██████╗ ████████╗██╗      ██████╗ ██╗     
██╔════╝██╔══██╗██╔═══██╗╚══██╔══╝██║      ██╔══██╗██║     
███████╗██████╔╝██║   ██║   ██║   ██║█████╗██║  ██║██║     
╚════██║██╔═══╝ ██║   ██║   ██║   ██║╚════╝██║  ██║██║     
███████║██║     ╚██████╔╝   ██║   ██║      ██████╔╝███████╗
╚══════╝╚═╝      ╚═════╝    ╚═╝   ╚═╝      ╚═════╝ ╚══════╝
                                                           
    """
    console.print(banner, style="bold cyan")
    console.print(
        Panel.fit(
            "[bold white]Download entire Spotify playlists as high-quality MP3s[/bold white]\n"
            "[dim]Created by Malik Johnson (https://github.com/DevArqf)[/dim]",
            border_style="cyan",
            box=box.DOUBLE
        )
    )
    console.print()

def get_spotify_client(config):
    with console.status("[bold cyan]Authenticating with Spotify...", spinner="dots"):
        try:
            scope = "playlist-read-private playlist-read-collaborative"
            sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=config['spotify']['client_id'],
                client_secret=config['spotify']['client_secret'],
                redirect_uri=config['spotify']['redirect_uri'],
                scope=scope
            ))
            sp.current_user()
            return sp
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Authentication failed: {str(e)}")
            raise

def get_playlist_tracks(sp, playlist_id):
    tracks = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Fetching playlist tracks...", total=None)
        
        results = sp.playlist_tracks(playlist_id)
        
        while results:
            for item in results['items']:
                track = item['track']
                if track:
                    tracks.append({
                        'name': track['name'],
                        'artist': ', '.join([artist['name'] for artist in track['artists']]),
                        'album': track['album']['name'],
                        'duration': track['duration_ms'] // 1000
                    })
            
            results = sp.next(results) if results['next'] else None
        
        progress.update(task, completed=True)
    
    return tracks

def display_playlist_info(tracks, playlist_name, config):
    if not config['display']['show_preview']:
        return
    
    table = Table(
        title=f"📀 [bold cyan]{playlist_name}[/bold cyan]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("#", style="dim", width=4)
    table.add_column("Track", style="cyan", no_wrap=False)
    table.add_column("Artist", style="green", no_wrap=False)
    table.add_column("Duration", justify="right", style="yellow")
    
    total_duration = 0
    preview_count = config['display']['preview_count']
    
    for i, track in enumerate(tracks[:preview_count], 1):
        minutes = track['duration'] // 60
        seconds = track['duration'] % 60
        duration_str = f"{minutes}:{seconds:02d}"
        total_duration += track['duration']
        
        table.add_row(
            str(i),
            track['name'],
            track['artist'],
            duration_str
        )
    
    if len(tracks) > preview_count:
        table.add_row("...", "[dim]... and more[/dim]", "", "")
    
    console.print(table)
    
    # Calculate total duration
    for track in tracks[preview_count:]:
        total_duration += track['duration']
    
    total_mins = total_duration // 60
    total_hours = total_mins // 60
    remaining_mins = total_mins % 60
    
    summary = Panel(
        f"[bold white]Total Tracks:[/bold white] [cyan]{len(tracks)}[/cyan]\n"
        f"[bold white]Total Duration:[/bold white] [cyan]{total_hours}h {remaining_mins}m[/cyan]\n"
        f"[bold white]Download Location:[/bold white] [cyan]{Path(config['download']['output_directory']).absolute()}[/cyan]\n"
        f"[bold white]Parallel Downloads:[/bold white] [cyan]{config['download']['parallel_downloads']}[/cyan]\n"
        f"[bold white]Audio Format:[/bold white] [cyan]{config['download']['audio_format'].upper()}[/cyan] @ [cyan]{config['download']['audio_quality']}kbps[/cyan]",
        title="[bold]Summary[/bold]",
        border_style="green",
        box=box.ROUNDED
    )
    console.print(summary)
    console.print()

def file_exists(track_info, output_dir, audio_format):
    artist = track_info['artist'].replace('/', '_').replace('\\', '_')
    title = track_info['name'].replace('/', '_').replace('\\', '_')
    possible_names = [
        f"{artist} - {title}.{audio_format}",
        f"{title}.{audio_format}"
    ]
    
    for name in possible_names:
        if (Path(output_dir) / name).exists():
            return True
    return False

def download_track(track_info, output_dir, config):
    search_query = f"{track_info['artist']} - {track_info['name']}"
    
    if config['download']['skip_existing'] and file_exists(track_info, output_dir, config['download']['audio_format']):
        return {'status': 'skipped', 'track': search_query}
    
    artist = track_info['artist'].replace('/', '_').replace('\\', '_')
    title = track_info['name'].replace('/', '_').replace('\\', '_')
    clean_filename = f"{artist} - {title}" if artist and artist.lower() != 'na' else title
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, f'{clean_filename}.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': config['download']['audio_format'],
            'preferredquality': config['download']['audio_quality'],
        }],
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'keepvideo': False,
        'prefer_ffmpeg': True,
        'postprocessor_args': [
            '-ar', '44100'
        ],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
            return {'status': 'success', 'track': search_query}
    except Exception as e:
        return {'status': 'failed', 'track': search_query, 'error': str(e)}

def download_tracks_parallel(tracks, output_dir, config, progress):
    max_workers = config['download']['parallel_downloads']
    
    overall_task = progress.add_task(
        "[cyan]Downloading playlist...", 
        total=len(tracks)
    )
    
    successful = 0
    failed = 0
    skipped = 0
    failed_tracks = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_track = {
            executor.submit(download_track, track, output_dir, config): track 
            for track in tracks
        }
        
        for future in as_completed(future_to_track):
            track = future_to_track[future]
            try:
                result = future.result()
                
                if result['status'] == 'success':
                    successful += 1
                    console.print(f"[green]✓[/green] {result['track']}")
                elif result['status'] == 'skipped':
                    skipped += 1
                    console.print(f"[yellow]⊘[/yellow] {result['track']} [dim](already exists)[/dim]")
                else:
                    failed += 1
                    failed_tracks.append(result['track'])
                    console.print(f"[red]✗[/red] {result['track']}")
                
                progress.update(overall_task, advance=1)
                
            except Exception as e:
                failed += 1
                track_name = f"{track['artist']} - {track['name']}"
                failed_tracks.append(track_name)
                console.print(f"[red]✗[/red] {track_name} [dim](exception)[/dim]")
                progress.update(overall_task, advance=1)
    
    return successful, failed, skipped, failed_tracks

def main():
    print_banner()
    
    if not check_ffmpeg():
        console.print("[bold red]✗ FFmpeg not found![/bold red]")
        console.print("\nFFmpeg is required for audio conversion. Please install it:")
        console.print("  • Windows: [cyan]winget install -e --id Gyan.FFmpeg[/cyan]")
        console.print("  • macOS: [cyan]brew install ffmpeg[/cyan]")
        console.print("  • Linux: [cyan]sudo apt install ffmpeg[/cyan]")
        console.print("\nAfter installation, restart this script.\n")
        sys.exit(1)
    
    if not config_exists():
        console.print("[yellow]No configuration found. Starting setup wizard...[/yellow]\n")
        config = setup_wizard()
    else:
        config = load_config()
    
    if not validate_config(config):
        console.print("[yellow]Spotify credentials not configured. Running setup wizard...[/yellow]\n")
        config = setup_wizard()
    
    output_dir = Path(config['download']['output_directory'])
    output_dir.mkdir(exist_ok=True)
    
    console.print("[1] Download playlist")
    console.print("[2] Configure settings")
    console.print("[0] Exit")
    console.print()
    
    choice = Prompt.ask("[cyan]Select option[/cyan]", choices=['0','1','2'])
    
    if choice == '2':
        config = show_config_menu(config)
        return main()
    elif choice == '0':
        console.print("[yellow]Goodbye![/yellow]\n")
        return
    
    console.print()
    
    try:
        sp = get_spotify_client(config)
        console.print("[bold green]✓[/bold green] Successfully authenticated with Spotify!\n")
    except Exception as e:
        console.print("[bold red]✗[/bold red] Failed to authenticate. Check your credentials in config.\n")
        return
    
    playlist_url = Prompt.ask(
        "[bold cyan]Enter your Spotify playlist URL or ID[/bold cyan]",
        default=""
    )
    
    if not playlist_url:
        console.print("[bold red]✗[/bold red] No playlist URL provided. Exiting.\n")
        return
    
    if 'playlist/' in playlist_url:
        playlist_id = playlist_url.split('playlist/')[-1].split('?')[0]
    else:
        playlist_id = playlist_url
    
    console.print()
    
    try:
        tracks = get_playlist_tracks(sp, playlist_id)
        playlist_info = sp.playlist(playlist_id)
        playlist_name = playlist_info['name']
        
        console.print(f"[bold green]✓[/bold green] Found {len(tracks)} tracks in playlist!\n")
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to fetch playlist: {str(e)}\n")
        return
    
    display_playlist_info(tracks, playlist_name, config)
    
    if not Confirm.ask("[bold yellow]Start downloading?[/bold yellow]", default=True):
        console.print("\n[bold yellow]Download cancelled.[/bold yellow]\n")
        return
    
    console.print()
    
    start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        successful, failed, skipped, failed_tracks = download_tracks_parallel(
            tracks, output_dir, config, progress
        )
    
    elapsed_time = time.time() - start_time
    
    console.print()
    
    results_table = Table(
        title="[bold]Download Summary[/bold]",
        box=box.DOUBLE_EDGE,
        show_header=True,
        header_style="bold cyan"
    )
    
    results_table.add_column("Status", style="bold", width=20)
    results_table.add_column("Count", justify="right", style="bold", width=10)
    
    results_table.add_row("[green]✓ Successful[/green]", f"[green]{successful}[/green]")
    results_table.add_row("[yellow]⊘ Skipped[/yellow]", f"[yellow]{skipped}[/yellow]")
    results_table.add_row("[red]✗ Failed[/red]", f"[red]{failed}[/red]")
    results_table.add_row("[cyan]Total[/cyan]", f"[cyan]{len(tracks)}[/cyan]")
    
    console.print(results_table)
    console.print(f"\n[dim]Completed in {elapsed_time:.1f} seconds[/dim]")
    
    if failed_tracks:
        console.print("\n[bold yellow]Failed Downloads:[/bold yellow]")
        for track in failed_tracks:
            console.print(f"  [red]•[/red] {track}")
    
    console.print(
        f"\n[bold green]✓ Downloads complete![/bold green] Check: [cyan]{output_dir.absolute()}[/cyan]\n"
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Download interrupted by user. Exiting...[/bold yellow]\n")
    except Exception as e:
        console.print(f"\n[bold red]An unexpected error occurred: {str(e)}[/bold red]\n")