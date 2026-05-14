function createDefaultConfig() {
    return {
        spotify: {
            client_id: '',
            client_secret: '',
            redirect_uri: 'http://127.0.0.1:9090',
        },
        download: {
            output_directory: '',
            audio_format: 'mp3',
            audio_quality: '320',
            parallel_downloads: 5,
            youtube_cookies_browser: '',
            youtube_cookies_file: '',
        },
        display: {
            theme: 'dark',
        },
    };
}

module.exports = {
    createDefaultConfig,
};
