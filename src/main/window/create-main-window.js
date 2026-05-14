const path = require('path');
const { BrowserWindow } = require('electron');

function createMainWindow() {
    const mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 900,
        minHeight: 600,
        resizable: false,
        maximizable: true,
        minimizable: true,
        fullscreenable: false,
        frame: false,
        transparent: true,
        backgroundColor: '#00000000',
        icon: path.join(__dirname, '..', '..', '..', 'resources', 'icons', 'icon.png'),
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
        },
    });

    mainWindow.loadFile(path.join(__dirname, '..', '..', 'renderer', 'index.html'));
    return mainWindow;
}

module.exports = {
    createMainWindow,
};
