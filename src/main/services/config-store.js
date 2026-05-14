const fs = require('fs');
const path = require('path');
const { app } = require('electron');
const { createDefaultConfig } = require('../../shared/default-config');

function getConfigPath() {
    return path.join(app.getPath('userData'), 'config.json');
}

function mergeConfigWithDefaults(config = {}) {
    const defaults = createDefaultConfig();

    return {
        spotify: {
            ...defaults.spotify,
            ...(config.spotify || {}),
        },
        download: {
            ...defaults.download,
            ...(config.download || {}),
        },
        display: {
            ...defaults.display,
            ...(config.display || {}),
        },
    };
}

function loadConfig() {
    const configPath = getConfigPath();

    try {
        if (!fs.existsSync(configPath)) {
            return createDefaultConfig();
        }

        const rawConfig = fs.readFileSync(configPath, 'utf8');
        return mergeConfigWithDefaults(JSON.parse(rawConfig));
    } catch (error) {
        console.error('Failed to load config:', error);
        return createDefaultConfig();
    }
}

function saveConfig(config) {
    const configPath = getConfigPath();

    try {
        const normalizedConfig = mergeConfigWithDefaults(config);
        fs.writeFileSync(configPath, JSON.stringify(normalizedConfig, null, 4));
        return true;
    } catch (error) {
        console.error('Failed to save config:', error);
        return false;
    }
}

module.exports = {
    loadConfig,
    saveConfig,
};
