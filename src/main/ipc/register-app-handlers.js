const { dialog, ipcMain, shell } = require('electron');
const { loadConfig, saveConfig } = require('../services/config-store');
const { runJsonScript, startDownloadProcess } = require('../services/python-service');

function registerAppHandlers({ getMainWindow, getDownloadProcess, setDownloadProcess }) {
    ipcMain.handle('dialog:select-directory', async () => {
        const result = await dialog.showOpenDialog(getMainWindow(), {
            properties: ['openDirectory'],
        });

        return result.filePaths[0];
    });

    ipcMain.handle('dialog:select-file', async (event, options = {}) => {
        const result = await dialog.showOpenDialog(getMainWindow(), {
            properties: ['openFile'],
            filters: options.filters || [],
        });

        return result.filePaths[0];
    });

    ipcMain.handle('filesystem:open-directory', async (event, directoryPath) => {
        await shell.openPath(directoryPath);
    });

    ipcMain.handle('config:load', async () => loadConfig());
    ipcMain.handle('config:save', async (event, config) => saveConfig(config));

    ipcMain.handle('playlist:fetch', async (event, playlistUrl, config) => {
        return runJsonScript('playlist_fetcher.py', [
            playlistUrl,
            config.spotify.client_id,
            config.spotify.client_secret,
            JSON.stringify(config),
        ]);
    });

    ipcMain.on('download:start', (event, tracks, config) => {
        const mainWindow = getMainWindow();
        if (!mainWindow) {
            return;
        }

        const childProcess = startDownloadProcess(
            tracks,
            config,
            (progress) => {
                mainWindow.webContents.send('download:progress', progress);
            },
            (success) => {
                mainWindow.webContents.send('download:complete', success);
                setDownloadProcess(null);
            },
        );

        setDownloadProcess(childProcess);
    });

    ipcMain.on('download:cancel', () => {
        const activeDownloadProcess = getDownloadProcess();
        if (!activeDownloadProcess) {
            return;
        }

        activeDownloadProcess.kill();
        setDownloadProcess(null);
        getMainWindow()?.webContents.send('download:cancelled');
    });
}

module.exports = {
    registerAppHandlers,
};
