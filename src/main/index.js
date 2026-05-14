const { app, BrowserWindow } = require('electron');
const { createMainWindow } = require('./window/create-main-window');
const { registerWindowControls } = require('./ipc/register-window-controls');
const { registerAppHandlers } = require('./ipc/register-app-handlers');

let mainWindow = null;
let downloadProcess = null;

function getMainWindow() {
    return mainWindow;
}

function getDownloadProcess() {
    return downloadProcess;
}

function setDownloadProcess(childProcess) {
    downloadProcess = childProcess;
}

function openMainWindow() {
    mainWindow = createMainWindow();

    mainWindow.on('closed', () => {
        if (downloadProcess) {
            downloadProcess.kill();
            downloadProcess = null;
        }

        mainWindow = null;
    });
}

app.whenReady().then(() => {
    openMainWindow();

    registerWindowControls(getMainWindow);
    registerAppHandlers({
        getMainWindow,
        getDownloadProcess,
        setDownloadProcess,
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        openMainWindow();
    }
});
