const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');

const SUPPRESSED_STDERR_MARKERS = [
    'Private video',
    'Video unavailable',
    'This video is unavailable',
    'Requested format is not available',
    "Sign in if you've been granted access to this video",
    "This content isn't available",
    'The uploader has not made this video available',
];

function shouldSuppressPythonStderr(message) {
    const text = String(message || '');
    return SUPPRESSED_STDERR_MARKERS.some((marker) => text.includes(marker));
}

function resolveBackendScript(filename) {
    return path.join(__dirname, '..', '..', 'backend', filename);
}

function runJsonScript(filename, args) {
    return new Promise((resolve, reject) => {
        const scriptPath = resolveBackendScript(filename);
        const childProcess = spawn('python', [scriptPath, ...args]);
        let stdoutBuffer = '';

        childProcess.stdout.on('data', (data) => {
            stdoutBuffer += data.toString();
        });

        childProcess.stderr.on('data', (data) => {
            const message = data.toString();
            if (!shouldSuppressPythonStderr(message)) {
                console.error(`Python Error: ${message}`);
            }
        });

        childProcess.on('close', (code) => {
            if (code !== 0) {
                reject(new Error(`Python script failed: ${filename}`));
                return;
            }

            try {
                resolve(JSON.parse(stdoutBuffer));
            } catch (error) {
                reject(new Error(`Failed to parse JSON from ${filename}`));
            }
        });
    });
}

function createDownloadPayloadFile(tracks, config) {
    const payloadPath = path.join(
        os.tmpdir(),
        `playlist-audio-downloader-${Date.now()}-${Math.random().toString(16).slice(2)}.json`,
    );

    fs.writeFileSync(
        payloadPath,
        JSON.stringify({
            tracks,
            config,
        }),
        'utf8',
    );

    return payloadPath;
}

function startDownloadProcess(tracks, config, onProgress, onComplete) {
    const scriptPath = resolveBackendScript('track_downloader.py');
    const payloadPath = createDownloadPayloadFile(tracks, config);
    const childProcess = spawn('python', [scriptPath, payloadPath]);

    childProcess.stdout.on('data', (data) => {
        const lines = data.toString().split('\n');

        for (const line of lines) {
            if (!line.trim()) {
                continue;
            }

            try {
                onProgress(JSON.parse(line));
            } catch (error) {
                console.log('Python Output:', line);
            }
        }
    });

    childProcess.stderr.on('data', (data) => {
        const message = data.toString();
        if (!shouldSuppressPythonStderr(message)) {
            console.error(`Download Error: ${message}`);
        }
    });

    childProcess.on('close', (code) => {
        try {
            fs.unlinkSync(payloadPath);
        } catch (error) {
            console.warn(`Failed to remove temporary download payload: ${payloadPath}`);
        }
        onComplete(code === 0);
    });

    return childProcess;
}

module.exports = {
    runJsonScript,
    startDownloadProcess,
};
