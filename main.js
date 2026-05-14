const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let pythonProcess = null;

function shouldSuppressPythonStderr(message) {
    const text = String(message || '');
    const suppressedMarkers = [
        'Private video',
        'Video unavailable',
        'This video is unavailable',
        'Requested format is not available',
        "Sign in if you've been granted access to this video",
        "This content isn't available",
        'The uploader has not made this video available'
    ];

    return suppressedMarkers.some(marker => text.includes(marker));
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 900,
        minHeight: 600,
        frame: false,
        transparent: true,
        backgroundColor: '#00000000',
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            enableRemoteModule: true
        },
        icon: path.join(__dirname, 'assets', 'icon.png')
    });

    mainWindow.loadFile('index.html');

    mainWindow.on('closed', () => {
        if (pythonProcess) {
            pythonProcess.kill();
        }
        mainWindow = null;
    });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

ipcMain.on('minimize-window', () => {
    mainWindow.minimize();
});

ipcMain.on('maximize-window', () => {
    if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
    } else {
        mainWindow.maximize();
    }
});

ipcMain.on('close-window', () => {
    mainWindow.close();
});

ipcMain.handle('select-directory', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory']
    });
    return result.filePaths[0];
});

ipcMain.handle('select-file', async (event, options = {}) => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile'],
        filters: options.filters || []
    });
    return result.filePaths[0];
});

ipcMain.handle('open-directory', async (event, dirPath) => {
    shell.openPath(dirPath);
});

ipcMain.handle('load-config', async () => {
    const configPath = path.join(app.getPath('userData'), 'config.json');
    try {
        if (fs.existsSync(configPath)) {
            const data = fs.readFileSync(configPath, 'utf8');
            return JSON.parse(data);
        }
    } catch (error) {
        console.error('Error loading config:', error);
    }
    return null;
});

ipcMain.handle('save-config', async (event, config) => {
    const configPath = path.join(app.getPath('userData'), 'config.json');
    try {
        fs.writeFileSync(configPath, JSON.stringify(config, null, 4));
        return true;
    } catch (error) {
        console.error('Error saving config:', error);
        return false;
    }
});

ipcMain.handle('fetch-playlist', async (event, playlistUrl, config) => {
    return new Promise((resolve, reject) => {
        const pythonScript = path.join(__dirname, 'backend', 'fetch_playlist.py');
        const python = spawn('python', [
            pythonScript,
            playlistUrl,
            config.spotify.client_id,
            config.spotify.client_secret,
            JSON.stringify(config)
        ]);

        let dataString = '';

        python.stdout.on('data', (data) => {
            dataString += data.toString();
        });

        python.stderr.on('data', (data) => {
            const message = data.toString();
            if (!shouldSuppressPythonStderr(message)) {
                console.error(`Python Error: ${message}`);
            }
        });

        python.on('close', (code) => {
            if (code === 0) {
                try {
                    const result = JSON.parse(dataString);
                    resolve(result);
                } catch (error) {
                    reject(new Error('Failed to parse playlist data'));
                }
            } else {
                reject(new Error('Failed to fetch playlist'));
            }
        });
    });
});

ipcMain.on('start-download', (event, tracks, config) => {
    const pythonScript = path.join(__dirname, 'backend', 'download_tracks.py');
    
    pythonProcess = spawn('python', [
        pythonScript,
        JSON.stringify(tracks),
        JSON.stringify(config)
    ]);

    pythonProcess.stdout.on('data', (data) => {
        const lines = data.toString().split('\n');
        lines.forEach(line => {
            if (line.trim()) {
                try {
                    const progress = JSON.parse(line);
                    mainWindow.webContents.send('download-progress', progress);
                } catch (error) {
                    console.log('Output:', line);
                }
            }
        });
    });

    pythonProcess.stderr.on('data', (data) => {
        const message = data.toString();
        if (!shouldSuppressPythonStderr(message)) {
            console.error(`Download Error: ${message}`);
        }
    });

    pythonProcess.on('close', (code) => {
        mainWindow.webContents.send('download-complete', code === 0);
        pythonProcess = null;
    });
});

ipcMain.on('cancel-download', () => {
    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
        mainWindow.webContents.send('download-cancelled');
    }
});
