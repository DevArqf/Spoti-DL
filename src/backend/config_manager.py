import json
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich import box

console = Console()

CONFIG_FILE = Path('config.json')

DEFAULT_CONFIG = {
    'spotify': {
        'client_id': '',
        'client_secret': '',
        'redirect_uri': 'http://127.0.0.1:9090'
    },
    'download': {
        'output_directory': 'spotify_downloads',
        'audio_format': 'mp3',
        'audio_quality': '320',
        'parallel_downloads': 5,
        'skip_existing': True,
        'youtube_cookies_browser': '',
        'youtube_cookies_file': ''
    },
    'display': {
        'show_preview': True,
        'preview_count': 10,
        'theme': 'dark'
    }
}

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]
                    elif isinstance(DEFAULT_CONFIG[key], dict):
                        for subkey in DEFAULT_CONFIG[key]:
                            if subkey not in config[key]:
                                config[key][subkey] = DEFAULT_CONFIG[key][subkey]
                return config
        except json.JSONDecodeError:
            console.print("[bold red]Error reading config file. Using defaults.[/bold red]")
            return DEFAULT_CONFIG.copy()
    else:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    console.print(f"[green]Configuration saved to {CONFIG_FILE}[/green]")

def setup_wizard():
    console.print(Panel.fit(
        "[bold cyan]First Time Setup[/bold cyan]\n\n"
        "Let's configure your Spotify API credentials and download preferences.",
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print()
    
    config = DEFAULT_CONFIG.copy()
    
    console.print("[bold cyan]Spotify API Configuration[/bold cyan]")
    console.print("Get your credentials from: https://developer.spotify.com/dashboard\n")
    
    config['spotify']['client_id'] = Prompt.ask("[cyan]Client ID[/cyan]")
    config['spotify']['client_secret'] = Prompt.ask("[cyan]Client Secret[/cyan]", password=True)
    
    console.print()
    
    console.print("[bold cyan]Download Preferences[/bold cyan]\n")
    
    output_dir = Prompt.ask(
        "[cyan]Output directory[/cyan]",
        default=DEFAULT_CONFIG['download']['output_directory']
    )
    config['download']['output_directory'] = output_dir
    
    audio_format = Prompt.ask(
        "[cyan]Audio format[/cyan]",
        choices=['mp3', 'flac', 'm4a', 'opus', 'wav'],
        default='mp3'
    )
    config['download']['audio_format'] = audio_format
    
    if audio_format in ['mp3', 'm4a']:
        quality = Prompt.ask(
            "[cyan]Audio quality (kbps)[/cyan]",
            choices=['128', '192', '256', '320'],
            default='320'
        )
        config['download']['audio_quality'] = quality
    
    parallel = IntPrompt.ask(
        "[cyan]Parallel downloads (1-10)[/cyan]",
        default=5
    )
    config['download']['parallel_downloads'] = max(1, min(10, parallel))
    
    console.print()
    save_config(config)
    console.print()
    
    return config

def show_config_menu(config):
    while True:
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]Configuration Menu[/bold cyan]",
            border_style="cyan"
        ))
        console.print()
        
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Output Directory", config['download']['output_directory'])
        table.add_row("Audio Format", config['download']['audio_format'])
        table.add_row("Audio Quality", f"{config['download']['audio_quality']}kbps")
        table.add_row("Parallel Downloads", str(config['download']['parallel_downloads']))
        table.add_row("YouTube Cookies Browser", config['download']['youtube_cookies_browser'] or "Disabled")
        table.add_row("YouTube Cookies File", config['download']['youtube_cookies_file'] or "Not set")
        table.add_row("Skip Existing Files", str(config['download']['skip_existing']))
        table.add_row("Show Preview", str(config['display']['show_preview']))
        table.add_row("Theme", config['display']['theme'])
        
        console.print(table)
        console.print()
        
        console.print("[1] Change output directory")
        console.print("[2] Change audio format")
        console.print("[3] Change audio quality")
        console.print("[4] Change parallel downloads")
        console.print("[5] Set YouTube cookies browser")
        console.print("[6] Set YouTube cookies file")
        console.print("[7] Toggle skip existing files")
        console.print("[8] Toggle preview display")
        console.print("[9] Change theme")
        console.print("[10] Reset to defaults")
        console.print("[11] Save and exit")
        console.print("[0] Exit without saving")
        console.print()
        
        choice = Prompt.ask("[cyan]Select option[/cyan]", choices=['0','1','2','3','4','5','6','7','8','9','10','11'])
        
        if choice == '1':
            config['download']['output_directory'] = Prompt.ask(
                "[cyan]Output directory[/cyan]",
                default=config['download']['output_directory']
            )
        elif choice == '2':
            config['download']['audio_format'] = Prompt.ask(
                "[cyan]Audio format[/cyan]",
                choices=['mp3', 'flac', 'm4a', 'opus', 'wav'],
                default=config['download']['audio_format']
            )
        elif choice == '3':
            config['download']['audio_quality'] = Prompt.ask(
                "[cyan]Audio quality (kbps)[/cyan]",
                choices=['128', '192', '256', '320'],
                default=config['download']['audio_quality']
            )
        elif choice == '4':
            parallel = IntPrompt.ask(
                "[cyan]Parallel downloads (1-10)[/cyan]",
                default=config['download']['parallel_downloads']
            )
            config['download']['parallel_downloads'] = max(1, min(10, parallel))
        elif choice == '5':
            config['download']['youtube_cookies_browser'] = Prompt.ask(
                "[cyan]YouTube cookies browser[/cyan]",
                choices=['', 'chrome', 'edge', 'firefox', 'brave'],
                default=config['download']['youtube_cookies_browser']
            )
        elif choice == '6':
            config['download']['youtube_cookies_file'] = Prompt.ask(
                "[cyan]YouTube cookies file[/cyan]",
                default=config['download']['youtube_cookies_file']
            )
        elif choice == '7':
            config['download']['skip_existing'] = not config['download']['skip_existing']
        elif choice == '8':
            config['display']['show_preview'] = not config['display']['show_preview']
        elif choice == '9':
            config['display']['theme'] = Prompt.ask(
                "[cyan]Theme[/cyan]",
                choices=['dark', 'light'],
                default=config['display']['theme']
            )
        elif choice == '10':
            if Confirm.ask("[yellow]Reset all settings to defaults?[/yellow]"):
                config = DEFAULT_CONFIG.copy()
                console.print("[green]Settings reset to defaults[/green]")
                time.sleep(1)
        elif choice == '11':
            save_config(config)
            break
        elif choice == '0':
            break
    
    return config

def config_exists():
    return CONFIG_FILE.exists()

def validate_config(config):
    if not config['spotify']['client_id'] or not config['spotify']['client_secret']:
        return False
    return True
