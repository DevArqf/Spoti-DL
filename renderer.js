const { ipcRenderer, shell } = require('electron');

let currentConfig = null;
let currentTracks = [];

document.addEventListener('DOMContentLoaded', async () => {
    await loadConfig();
    initializeEventListeners();
});

function initializeEventListeners() {
    document.getElementById('minimize-btn').addEventListener('click', () => {
        ipcRenderer.send('minimize-window');
    });

    document.getElementById('maximize-btn').addEventListener('click', () => {
        ipcRenderer.send('maximize-window');
    });

    document.getElementById('close-btn').addEventListener('click', () => {
        ipcRenderer.send('close-window');
    });

    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const view = item.dataset.view;
            switchView(view);
        });
    });

    document.getElementById('fetch-btn').addEventListener('click', fetchPlaylist);
    document.getElementById('download-btn').addEventListener('click', startDownload);
    document.getElementById('cancel-btn').addEventListener('click', cancelDownload);
    
    document.getElementById('select-dir-btn').addEventListener('click', selectDirectory);
    document.getElementById('select-cookies-file-btn').addEventListener('click', selectCookiesFile);
    document.getElementById('save-settings-btn').addEventListener('click', saveSettings);
    document.getElementById('reset-settings-btn').addEventListener('click', resetSettings);

    document.getElementById('spotify-dev-link').addEventListener('click', (e) => {
        e.preventDefault();
        shell.openExternal('https://developer.spotify.com/dashboard');
    });

    document.getElementById('github-link').addEventListener('click', (e) => {
        e.preventDefault();
        shell.openExternal('https://github.com/DevArqf/spoti-dl');
    });

    document.getElementById('website-link').addEventListener('click', (e) => {
        e.preventDefault();
        shell.openExternal('https://malikjohnson.info');
    });

    ipcRenderer.on('download-progress', (event, progress) => {
        updateDownloadProgress(progress);
    });

    ipcRenderer.on('download-complete', (event, success) => {
        onDownloadComplete(success);
    });

    ipcRenderer.on('download-cancelled', () => {
        showNotification('Download cancelled', 'error');
        resetDownloadView();
    });
}

function switchView(viewName) {
    document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    
    document.getElementById(`${viewName}-view`).classList.add('active');
    document.querySelector(`[data-view="${viewName}"]`).classList.add('active');
}

function detectPlaylistSource(url) {
    const lowerUrl = (url || '').toLowerCase();

    if (lowerUrl.includes('youtube.com') || lowerUrl.includes('youtu.be')) {
        return 'youtube';
    }

    if (lowerUrl.includes('spotify.com')) {
        return 'spotify';
    }

    return 'unknown';
}

async function loadConfig() {
    currentConfig = await ipcRenderer.invoke('load-config');
    
    if (!currentConfig) {
        currentConfig = {
            spotify: {
                client_id: '',
                client_secret: '',
                redirect_uri: 'http://127.0.0.1:9090'
            },
            download: {
                output_directory: '',
                audio_format: 'mp3',
                audio_quality: '320',
                parallel_downloads: 5,
                youtube_cookies_browser: '',
                youtube_cookies_file: ''
            }
        };
    }

    updateSettingsUI();
}

function updateSettingsUI() {
    document.getElementById('client-id').value = currentConfig.spotify.client_id || '';
    document.getElementById('client-secret').value = currentConfig.spotify.client_secret || '';
    document.getElementById('output-dir').value = currentConfig.download.output_directory || '';
    document.getElementById('audio-format').value = currentConfig.download.audio_format || 'mp3';
    document.getElementById('audio-quality').value = currentConfig.download.audio_quality || '320';
    document.getElementById('parallel-downloads').value = currentConfig.download.parallel_downloads || 5;
    document.getElementById('youtube-cookies-browser').value = currentConfig.download.youtube_cookies_browser || '';
    document.getElementById('youtube-cookies-file').value = currentConfig.download.youtube_cookies_file || '';
}

async function selectDirectory() {
    const directory = await ipcRenderer.invoke('select-directory');
    if (directory) {
        document.getElementById('output-dir').value = directory;
    }
}

async function selectCookiesFile() {
    const file = await ipcRenderer.invoke('select-file', {
        filters: [
            { name: 'Cookies', extensions: ['txt'] },
            { name: 'All Files', extensions: ['*'] }
        ]
    });
    if (file) {
        document.getElementById('youtube-cookies-file').value = file;
    }
}

async function saveSettings() {
    currentConfig.spotify.client_id = document.getElementById('client-id').value;
    currentConfig.spotify.client_secret = document.getElementById('client-secret').value;
    currentConfig.download.output_directory = document.getElementById('output-dir').value;
    currentConfig.download.audio_format = document.getElementById('audio-format').value;
    currentConfig.download.audio_quality = document.getElementById('audio-quality').value;
    currentConfig.download.parallel_downloads = parseInt(document.getElementById('parallel-downloads').value);
    currentConfig.download.youtube_cookies_browser = document.getElementById('youtube-cookies-browser').value;
    currentConfig.download.youtube_cookies_file = document.getElementById('youtube-cookies-file').value;

    const saved = await ipcRenderer.invoke('save-config', currentConfig);
    
    if (saved) {
        showNotification('Settings saved successfully!');
    } else {
        showNotification('Failed to save settings', 'error');
    }
}

function resetSettings() {
    currentConfig = {
        spotify: {
            client_id: '',
            client_secret: '',
            redirect_uri: 'http://127.0.0.1:9090'
        },
        download: {
            output_directory: '',
            audio_format: 'mp3',
            audio_quality: '320',
            parallel_downloads: 5,
            youtube_cookies_browser: '',
            youtube_cookies_file: ''
        }
    };
    
    updateSettingsUI();
    showNotification('Settings reset to defaults');
}

async function fetchPlaylist() {
    const playlistUrl = document.getElementById('playlist-url').value.trim();
    const playlistSource = detectPlaylistSource(playlistUrl);
    
    if (!playlistUrl) {
        showNotification('Please enter a playlist URL', 'error');
        return;
    }

    if (playlistSource === 'unknown') {
        showNotification('Use a Spotify playlist URL or a YouTube playlist URL', 'error');
        return;
    }

    if (playlistSource === 'spotify' && (!currentConfig.spotify.client_id || !currentConfig.spotify.client_secret)) {
        showNotification('Please configure Spotify credentials in Settings', 'error');
        switchView('settings');
        return;
    }

    const fetchBtn = document.getElementById('fetch-btn');
    fetchBtn.disabled = true;
    fetchBtn.innerHTML = '<span>Fetching...</span>';

    try {
        const result = await ipcRenderer.invoke('fetch-playlist', playlistUrl, currentConfig);
        
        if (result.error) {
            showNotification(result.error, 'error');
            return;
        }

        currentTracks = result.tracks;
        displayPlaylist(result);
        showNotification(`Found ${result.tracks.length} tracks!`);
        
    } catch (error) {
        showNotification('Failed to fetch playlist: ' + error.message, 'error');
    } finally {
        fetchBtn.disabled = false;
        fetchBtn.innerHTML = '<span>Fetch Playlist</span><svg viewBox="0 0 24 24"><path d="M4 12l1.41 1.41L11 7.83V20h2V7.83l5.58 5.59L20 12l-8-8-8 8z" fill="currentColor"/></svg>';
    }
}

function displayPlaylist(playlistData) {
    document.getElementById('playlist-name').textContent = playlistData.name;
    document.getElementById('playlist-source').textContent = formatSourceLabel(playlistData.source_type);
    document.getElementById('track-count').textContent = `${playlistData.tracks.length} tracks`;
    
    const totalSeconds = playlistData.tracks.reduce((sum, track) => sum + track.duration, 0);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    document.getElementById('total-duration').textContent = `${hours}h ${minutes}m`;

    const tracksList = document.getElementById('tracks-list');
    tracksList.innerHTML = '';

    playlistData.tracks.slice(0, 10).forEach((track, index) => {
        const trackItem = document.createElement('div');
        trackItem.className = 'track-item';
        
        const minutes = Math.floor((track.duration || 0) / 60);
        const seconds = (track.duration || 0) % 60;
        const duration = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        trackItem.innerHTML = `
            <div class="track-number">${index + 1}</div>
            <div class="track-info">
                <div class="track-name">${escapeHtml(track.name || 'Unknown Title')}</div>
                <div class="track-artist">${escapeHtml(track.artist || 'Unknown Artist')}</div>
            </div>
            <div class="track-duration">${duration}</div>
        `;
        
        tracksList.appendChild(trackItem);
    });

    if (playlistData.tracks.length > 10) {
        const moreItem = document.createElement('div');
        moreItem.className = 'track-item';
        moreItem.innerHTML = `
            <div class="track-number">...</div>
            <div class="track-info">
                <div class="track-artist">And ${playlistData.tracks.length - 10} more tracks</div>
            </div>
        `;
        tracksList.appendChild(moreItem);
    }

    document.getElementById('playlist-preview').style.display = 'block';
}

function formatSourceLabel(sourceType) {
    if (sourceType === 'spotify_playlist') {
        return 'Spotify';
    }

    if (sourceType === 'youtube_playlist') {
        return 'YouTube';
    }

    return 'Playlist';
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function startDownload() {
    if (!currentTracks.length) {
        showNotification('Fetch a playlist before starting a download', 'error');
        return;
    }

    if (!currentConfig.download.output_directory) {
        showNotification('Please select an output directory in Settings', 'error');
        switchView('settings');
        return;
    }

    document.getElementById('playlist-preview').style.display = 'none';
    document.getElementById('download-progress').style.display = 'block';
    
    document.getElementById('success-count').textContent = '0';
    document.getElementById('skipped-count').textContent = '0';
    document.getElementById('failed-count').textContent = '0';
    document.getElementById('remaining-count').textContent = currentTracks.length;
    document.getElementById('progress-fill').style.width = '0%';
    document.getElementById('download-log').innerHTML = '';
    document.querySelectorAll('.open-folder-btn').forEach(button => button.remove());

    ipcRenderer.send('start-download', currentTracks, currentConfig);
}

function updateDownloadProgress(progress) {
    if (progress.type === 'success') {
        const successCount = parseInt(document.getElementById('success-count').textContent) + 1;
        document.getElementById('success-count').textContent = successCount;
        
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry success';
        logEntry.textContent = `OK ${progress.track}`;
        document.getElementById('download-log').appendChild(logEntry);
    } else if (progress.type === 'skipped') {
        const skippedCount = parseInt(document.getElementById('skipped-count').textContent) + 1;
        document.getElementById('skipped-count').textContent = skippedCount;

        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        logEntry.textContent = progress.error
            ? `SKIP ${progress.track}: ${progress.error}`
            : `SKIP ${progress.track}`;
        document.getElementById('download-log').appendChild(logEntry);
    } else if (progress.type === 'failed') {
        const failedCount = parseInt(document.getElementById('failed-count').textContent) + 1;
        document.getElementById('failed-count').textContent = failedCount;
        
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry error';
        logEntry.textContent = progress.error
            ? `X ${progress.track}: ${progress.error}`
            : `X ${progress.track}`;
        document.getElementById('download-log').appendChild(logEntry);
    }

    const successCount = parseInt(document.getElementById('success-count').textContent);
    const skippedCount = parseInt(document.getElementById('skipped-count').textContent);
    const failedCount = parseInt(document.getElementById('failed-count').textContent);
    const completed = successCount + skippedCount + failedCount;
    const remaining = currentTracks.length - completed;
    
    document.getElementById('remaining-count').textContent = remaining;
    
    const progressPercent = (completed / currentTracks.length) * 100;
    document.getElementById('progress-fill').style.width = `${progressPercent}%`;
    
    if (progress.current) {
        document.getElementById('current-track').textContent = `Currently downloading: ${progress.current}`;
    }

    const log = document.getElementById('download-log');
    log.scrollTop = log.scrollHeight;
}

function onDownloadComplete(success) {
    document.getElementById('current-track').textContent = success ? 'Download complete!' : 'Download completed with errors';
    document.getElementById('cancel-btn').style.display = 'none';
    
    showNotification(success ? 'All downloads completed!' : 'Downloads completed with some failures');
    
    setTimeout(() => {
        const openDirBtn = document.createElement('button');
        openDirBtn.className = 'btn-primary open-folder-btn';
        openDirBtn.innerHTML = '<span>Open Download Folder</span>';
        openDirBtn.style.marginTop = '16px';
        openDirBtn.addEventListener('click', () => {
            ipcRenderer.invoke('open-directory', currentConfig.download.output_directory);
        });
        
        document.querySelector('.progress-header').appendChild(openDirBtn);
    }, 500);
}

function cancelDownload() {
    ipcRenderer.send('cancel-download');
}

function resetDownloadView() {
    document.getElementById('download-progress').style.display = 'none';
    document.getElementById('playlist-preview').style.display = 'block';
    document.getElementById('cancel-btn').style.display = 'block';
    document.querySelectorAll('.open-folder-btn').forEach(button => button.remove());
}

function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    const notificationText = notification.querySelector('.notification-text');
    
    notificationText.textContent = message;
    notification.className = `notification ${type}`;
    notification.classList.add('show');
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}
