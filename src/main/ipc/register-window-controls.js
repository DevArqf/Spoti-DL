const { ipcMain } = require('electron');

function registerWindowControls(getMainWindow) {
    ipcMain.on('window:minimize', () => {
        getMainWindow()?.minimize();
    });

    ipcMain.on('window:maximize-toggle', () => {
        const mainWindow = getMainWindow();
        if (!mainWindow) {
            return;
        }

        if (mainWindow.isMaximized()) {
            mainWindow.unmaximize();
            return;
        }

        mainWindow.maximize();
    });

    ipcMain.on('window:close', () => {
        getMainWindow()?.close();
    });
}

module.exports = {
    registerWindowControls,
};
