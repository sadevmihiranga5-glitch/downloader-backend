const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');

const app = express();

app.use(cors({
    origin: '*',
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type']
}));

app.use(express.json());

app.post('/api/download', async (req, res) => {
    const { url } = req.body;
    if (!url) return res.status(400).json({ error: 'URL is required' });

    try {
        // Alternative Reliable Engine (AIO Video Downloader API)
        const apiUrl = `https://api.vkrdown.com/v1/download?url=${encodeURIComponent(url)}`;
        
        const response = await fetch(apiUrl, {
            method: 'GET',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        });

        if (!response.ok) {
            throw new Error('API Request failed');
        }

        const data = await response.json();

        // Extract direct video URL from response
        let downloadUrl = null;
        if (data.data && data.data.url) {
            downloadUrl = data.data.url;
        } else if (data.url) {
            downloadUrl = data.url;
        } else if (data.downloadUrl) {
            downloadUrl = data.downloadUrl;
        } else if (data.data && Array.isArray(data.data.downloads) && data.data.downloads.length > 0) {
            downloadUrl = data.data.downloads[0].url;
        }

        if (downloadUrl) {
            return res.json({
                url: downloadUrl,
                filename: 'video_download',
                type: 'video'
            });
        } else {
            return res.status(422).json({ error: 'Could not parse download link. Please check the URL.' });
        }

    } catch (error) {
        return res.status(500).json({ error: 'Failed to extract video. Please try again.' });
    }
});

module.exports = app;
