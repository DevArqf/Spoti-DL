const { ipcRenderer, shell } = require('electron');
const { createDefaultConfig } = require('../shared/default-config');

const PLAYLIST_FETCH_BUTTON_DEFAULT_HTML = `
    <span>Fetch Playlist</span>
    <svg viewBox="0 0 24 24"><path d="M4 12l1.41 1.41L11 7.83V20h2V7.83l5.58 5.59L20 12l-8-8-8 8z" fill="currentColor"/></svg>
`;

const EXTERNAL_LINKS = {
    github: 'https://github.com/DevArqf/spoti-dl',
    spotifyDeveloperDashboard: 'https://developer.spotify.com/dashboard',
    website: 'https://malikjohnson.info',
};

let currentConfig = createDefaultConfig();
let currentTracks = [];

document.addEventListener('DOMContentLoaded', async () => {
    cacheDomReferences();
    await initializeApp();
});

const ui = {};

function cacheDomReferences() {
    ui.cancelButton = document.getElementById('cancel-btn');
    ui.clientIdInput = document.getElementById('client-id');
    ui.clientSecretInput = document.getElementById('client-secret');
    ui.closeButton = document.getElementById('close-btn');
    ui.currentTrack = document.getElementById('current-track');
    ui.downloadButton = document.getElementById('download-btn');
    ui.downloadLog = document.getElementById('download-log');
    ui.downloadProgress = document.getElementById('download-progress');
    ui.failedCount = document.getElementById('failed-count');
    ui.fetchButton = document.getElementById('fetch-btn');
    ui.githubLink = document.getElementById('github-link');
    ui.maximizeButton = document.getElementById('maximize-btn');
    ui.minimizeButton = document.getElementById('minimize-btn');
    ui.notification = document.getElementById('notification');
    ui.notificationText = ui.notification.querySelector('.notification-text');
    ui.openDirectoryButtonsSelector = '.open-folder-btn';
    ui.outputDirectoryInput = document.getElementById('output-dir');
    ui.parallelDownloadsInput = document.getElementById('parallel-downloads');
    ui.playlistName = document.getElementById('playlist-name');
    ui.playlistPreview = document.getElementById('playlist-preview');
    ui.playlistSource = document.getElementById('playlist-source');
    ui.playlistUrlInput = document.getElementById('playlist-url');
    ui.progressFill = document.getElementById('progress-fill');
    ui.remainingCount = document.getElementById('remaining-count');
    ui.resetSettingsButton = document.getElementById('reset-settings-btn');
    ui.saveSettingsButton = document.getElementById('save-settings-btn');
    ui.selectCookiesFileButton = document.getElementById('select-cookies-file-btn');
    ui.selectDirectoryButton = document.getElementById('select-dir-btn');
    ui.skippedCount = document.getElementById('skipped-count');
    ui.spotifyDeveloperLink = document.getElementById('spotify-dev-link');
    ui.successCount = document.getElementById('success-count');
    ui.themeSelect = document.getElementById('theme-select');
    ui.totalDuration = document.getElementById('total-duration');
    ui.trackCount = document.getElementById('track-count');
    ui.tracksList = document.getElementById('tracks-list');
    ui.websiteLink = document.getElementById('website-link');
    ui.youtubeCookiesBrowserSelect = document.getElementById('youtube-cookies-browser');
    ui.youtubeCookiesFileInput = document.getElementById('youtube-cookies-file');
    ui.audioFormatSelect = document.getElementById('audio-format');
    ui.audioQualitySelect = document.getElementById('audio-quality');
}

async function initializeApp() {
    registerEventListeners();
    await loadConfig();
}

function registerEventListeners() {
    ui.minimizeButton.addEventListener('click', () => ipcRenderer.send('window:minimize'));
    ui.maximizeButton.addEventListener('click', () => ipcRenderer.send('window:maximize-toggle'));
    ui.closeButton.addEventListener('click', () => ipcRenderer.send('window:close'));

    document.querySelectorAll('.nav-item').forEach((item) => {
        item.addEventListener('click', () => switchView(item.dataset.view));
    });

    ui.fetchButton.addEventListener('click', fetchPlaylist);
    ui.downloadButton.addEventListener('click', startDownload);
    ui.cancelButton.addEventListener('click', cancelDownload);
    ui.selectDirectoryButton.addEventListener('click', selectDirectory);
    ui.selectCookiesFileButton.addEventListener('click', selectCookiesFile);
    ui.saveSettingsButton.addEventListener('click', saveSettings);
    ui.resetSettingsButton.addEventListener('click', resetSettings);

    ui.playlistUrlInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            fetchPlaylist();
        }
    });

    ui.spotifyDeveloperLink.addEventListener('click', (event) => {
        event.preventDefault();
        shell.openExternal(EXTERNAL_LINKS.spotifyDeveloperDashboard);
    });

    ui.githubLink.addEventListener('click', (event) => {
        event.preventDefault();
        shell.openExternal(EXTERNAL_LINKS.github);
    });

    ui.websiteLink.addEventListener('click', (event) => {
        event.preventDefault();
        shell.openExternal(EXTERNAL_LINKS.website);
    });

    ipcRenderer.on('download:progress', (event, progress) => updateDownloadProgress(progress));
    ipcRenderer.on('download:complete', (event, success) => onDownloadComplete(success));
    ipcRenderer.on('download:cancelled', () => {
        showNotification('Download cancelled', 'error');
        resetDownloadView();
    });
}

async function loadConfig() {
    const savedConfig = await ipcRenderer.invoke('config:load');
    currentConfig = mergeConfig(savedConfig);

    applyTheme(currentConfig.display.theme);
    updateSettingsUI();
}

function mergeConfig(config) {
    return {
        ...createDefaultConfig(),
        ...config,
        spotify: {
            ...createDefaultConfig().spotify,
            ...(config?.spotify || {}),
        },
        download: {
            ...createDefaultConfig().download,
            ...(config?.download || {}),
        },
        display: {
            ...createDefaultConfig().display,
            ...(config?.display || {}),
        },
    };
}

function updateSettingsUI() {
    ui.clientIdInput.value = currentConfig.spotify.client_id || '';
    ui.clientSecretInput.value = currentConfig.spotify.client_secret || '';
    ui.outputDirectoryInput.value = currentConfig.download.output_directory || '';
    ui.audioFormatSelect.value = currentConfig.download.audio_format || 'mp3';
    ui.audioQualitySelect.value = currentConfig.download.audio_quality || '320';
    ui.parallelDownloadsInput.value = currentConfig.download.parallel_downloads || 5;
    ui.youtubeCookiesBrowserSelect.value = currentConfig.download.youtube_cookies_browser || '';
    ui.youtubeCookiesFileInput.value = currentConfig.download.youtube_cookies_file || '';
    ui.themeSelect.value = currentConfig.display.theme || 'dark';
}

async function selectDirectory() {
    const selectedDirectory = await ipcRenderer.invoke('dialog:select-directory');
    if (selectedDirectory) {
        ui.outputDirectoryInput.value = selectedDirectory;
    }
}

async function selectCookiesFile() {
    const selectedFile = await ipcRenderer.invoke('dialog:select-file', {
        filters: [
            { name: 'Cookies', extensions: ['txt'] },
            { name: 'All Files', extensions: ['*'] },
        ],
    });

    if (selectedFile) {
        ui.youtubeCookiesFileInput.value = selectedFile;
    }
}

async function saveSettings() {
    currentConfig = {
        ...currentConfig,
        spotify: {
            ...currentConfig.spotify,
            client_id: ui.clientIdInput.value,
            client_secret: ui.clientSecretInput.value,
        },
        download: {
            ...currentConfig.download,
            output_directory: ui.outputDirectoryInput.value,
            audio_format: ui.audioFormatSelect.value,
            audio_quality: ui.audioQualitySelect.value,
            parallel_downloads: parseInt(ui.parallelDownloadsInput.value, 10),
            youtube_cookies_browser: ui.youtubeCookiesBrowserSelect.value,
            youtube_cookies_file: ui.youtubeCookiesFileInput.value,
        },
        display: {
            ...currentConfig.display,
            theme: ui.themeSelect.value,
        },
    };

    applyTheme(currentConfig.display.theme);

    const saveSucceeded = await ipcRenderer.invoke('config:save', currentConfig);
    showNotification(
        saveSucceeded ? 'Settings saved successfully!' : 'Failed to save settings',
        saveSucceeded ? 'success' : 'error',
    );
}

function resetSettings() {
    currentConfig = createDefaultConfig();
    applyTheme(currentConfig.display.theme);
    updateSettingsUI();
    showNotification('Settings reset to defaults');
}

function applyTheme(theme) {
    document.body.dataset.theme = theme === 'light' ? 'light' : 'dark';
}

function switchView(viewName) {
    document.querySelectorAll('.view').forEach((view) => view.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach((item) => item.classList.remove('active'));

    document.getElementById(`${viewName}-view`).classList.add('active');
    document.querySelector(`[data-view="${viewName}"]`).classList.add('active');
}

function detectPlaylistSource(url) {
    const normalizedUrl = (url || '').toLowerCase();

    if (normalizedUrl.includes('youtube.com') || normalizedUrl.includes('youtu.be')) {
        return 'youtube';
    }

    if (normalizedUrl.includes('spotify.com')) {
        return 'spotify';
    }

    return 'unknown';
}

async function fetchPlaylist() {
    const playlistUrl = ui.playlistUrlInput.value.trim();
    const playlistSource = detectPlaylistSource(playlistUrl);

    if (!playlistUrl) {
        showNotification('Please enter a playlist URL', 'error');
        return;
    }

    if (playlistSource === 'unknown') {
        showNotification('Use a Spotify playlist URL or a YouTube playlist URL', 'error');
        return;
    }

    if (
        playlistSource === 'spotify' &&
        (!currentConfig.spotify.client_id || !currentConfig.spotify.client_secret)
    ) {
        showNotification('Please configure Spotify credentials in Settings', 'error');
        switchView('settings');
        return;
    }

    setFetchButtonState(true);

    try {
        const playlistData = await ipcRenderer.invoke('playlist:fetch', playlistUrl, currentConfig);
        if (playlistData.error) {
            showNotification(playlistData.error, 'error');
            return;
        }

        currentTracks = playlistData.tracks;
        displayPlaylist(playlistData);
        showNotification(`Found ${playlistData.tracks.length} tracks!`);
    } catch (error) {
        showNotification(`Failed to fetch playlist: ${error.message}`, 'error');
    } finally {
        setFetchButtonState(false);
    }
}

function setFetchButtonState(isLoading) {
    ui.fetchButton.disabled = isLoading;
    ui.fetchButton.innerHTML = isLoading ? '<span>Fetching...</span>' : PLAYLIST_FETCH_BUTTON_DEFAULT_HTML;
}

function displayPlaylist(playlistData) {
    ui.playlistName.textContent = playlistData.name;
    ui.playlistSource.textContent = formatSourceLabel(playlistData.source_type);
    ui.trackCount.textContent = `${playlistData.tracks.length} tracks`;

    const totalDurationSeconds = playlistData.tracks.reduce(
        (total, track) => total + (track.duration || 0),
        0,
    );
    const totalHours = Math.floor(totalDurationSeconds / 3600);
    const totalMinutes = Math.floor((totalDurationSeconds % 3600) / 60);
    ui.totalDuration.textContent = `${totalHours}h ${totalMinutes}m`;

    renderTrackPreview(playlistData.tracks);

    ui.playlistPreview.style.display = 'block';
    ui.downloadProgress.style.display = 'none';
}

function renderTrackPreview(tracks) {
    ui.tracksList.innerHTML = '';

    tracks.slice(0, 10).forEach((track, index) => {
        const trackItem = document.createElement('div');
        trackItem.className = 'track-item';

        const duration = formatTrackDuration(track.duration || 0);
        trackItem.innerHTML = `
            <div class="track-number">${index + 1}</div>
            <div class="track-info">
                <div class="track-name">${escapeHtml(track.name || 'Unknown Title')}</div>
                <div class="track-artist">${escapeHtml(track.artist || 'Unknown Artist')}</div>
            </div>
            <div class="track-duration">${duration}</div>
        `;

        ui.tracksList.appendChild(trackItem);
    });

    if (tracks.length <= 10) {
        return;
    }

    const moreTracksItem = document.createElement('div');
    moreTracksItem.className = 'track-item';
    moreTracksItem.innerHTML = `
        <div class="track-number">...</div>
        <div class="track-info">
            <div class="track-artist">And ${tracks.length - 10} more tracks</div>
        </div>
    `;

    ui.tracksList.appendChild(moreTracksItem);
}

function formatTrackDuration(durationSeconds) {
    const minutes = Math.floor(durationSeconds / 60);
    const seconds = durationSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
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

    resetProgressCounters();
    ui.playlistPreview.style.display = 'none';
    ui.downloadProgress.style.display = 'block';
    ui.currentTrack.textContent = `Preparing ${currentTracks.length} tracks for download...`;
    document.querySelectorAll(ui.openDirectoryButtonsSelector).forEach((button) => button.remove());

    ipcRenderer.send('download:start', currentTracks, currentConfig);
}

function resetProgressCounters() {
    ui.successCount.textContent = '0';
    ui.skippedCount.textContent = '0';
    ui.failedCount.textContent = '0';
    ui.remainingCount.textContent = currentTracks.length;
    ui.progressFill.style.width = '0%';
    ui.downloadLog.innerHTML = '';
}

function updateDownloadProgress(progress) {
    if (progress.type === 'success') {
        incrementCounter(ui.successCount);
        appendLogEntry(`OK ${progress.track}`, 'success');
    } else if (progress.type === 'skipped') {
        incrementCounter(ui.skippedCount);
        appendLogEntry(
            progress.error ? `SKIP ${progress.track}: ${progress.error}` : `SKIP ${progress.track}`,
        );
    } else if (progress.type === 'failed') {
        incrementCounter(ui.failedCount);
        appendLogEntry(
            progress.error ? `X ${progress.track}: ${progress.error}` : `X ${progress.track}`,
            'error',
        );
    }

    const completedCount =
        parseInt(ui.successCount.textContent, 10) +
        parseInt(ui.skippedCount.textContent, 10) +
        parseInt(ui.failedCount.textContent, 10);
    const remainingCount = currentTracks.length - completedCount;
    const completionPercent = (completedCount / currentTracks.length) * 100;

    ui.remainingCount.textContent = remainingCount;
    ui.progressFill.style.width = `${completionPercent}%`;

    if (progress.current) {
        ui.currentTrack.textContent = `Currently downloading: ${progress.current}`;
    }

    ui.downloadLog.scrollTop = ui.downloadLog.scrollHeight;
}

function incrementCounter(element) {
    element.textContent = String(parseInt(element.textContent, 10) + 1);
}

function appendLogEntry(message, className = '') {
    const logEntry = document.createElement('div');
    logEntry.className = className ? `log-entry ${className}` : 'log-entry';
    logEntry.textContent = message;
    ui.downloadLog.appendChild(logEntry);
}

function onDownloadComplete(success) {
    ui.currentTrack.textContent = success
        ? 'Download complete!'
        : 'Download completed with errors';
    ui.cancelButton.style.display = 'none';

    showNotification(
        success ? 'All downloads completed!' : 'Downloads completed with some failures',
        success ? 'success' : 'error',
    );

    setTimeout(() => {
        const openFolderButton = document.createElement('button');
        openFolderButton.className = 'btn-primary open-folder-btn';
        openFolderButton.innerHTML = '<span>Open Download Folder</span>';
        openFolderButton.style.marginTop = '16px';
        openFolderButton.addEventListener('click', () => {
            ipcRenderer.invoke('filesystem:open-directory', currentConfig.download.output_directory);
        });

        document.querySelector('.progress-header').appendChild(openFolderButton);
    }, 500);
}

function cancelDownload() {
    ipcRenderer.send('download:cancel');
}

function resetDownloadView() {
    ui.downloadProgress.style.display = 'none';
    ui.playlistPreview.style.display = currentTracks.length ? 'block' : 'none';
    ui.cancelButton.style.display = 'block';
    ui.currentTrack.textContent = '';
    document.querySelectorAll(ui.openDirectoryButtonsSelector).forEach((button) => button.remove());
}

function showNotification(message, type = 'success') {
    ui.notificationText.textContent = message;
    ui.notification.className = `notification ${type}`;
    ui.notification.classList.add('show');

    setTimeout(() => {
        ui.notification.classList.remove('show');
    }, 3000);
}
