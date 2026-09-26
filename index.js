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

// Multi-Instance Working Endpoints
const cobaltInstances = [
    'https://api.cobalt.tools/',
    'https://cobalt-api.kwi.li/',
    'https://co.wuk.sh/api/json'
];

app.post('/api/download', async (req, res) => {
    const { url } = req.body;
    if (!url) return res.status(400).json({ error: 'URL is required' });

    // 1. Try Rapid / Public Downloader API Engine
    try {
        const altRes = await fetch(`https://api.vkrdown.com/v1/download?url=${encodeURIComponent(url)}`, {
            headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }
        });
        
        if (altRes.ok) {
            const altData = await altRes.json();
            if (altData && (altData.url || altData.data?.url || altData.downloadUrl)) {
                return res.json({
                    url: altData.url || altData.data?.url || altData.downloadUrl,
                    filename: altData.title || 'video_download',
                    type: 'video'
                });
            }
        }
    } catch (e) {
        // Fallback to Cobalt Instances
    }

    // 2. Try Cobalt API Instances
    for (const instanceUrl of cobaltInstances) {
        try {
            const response = await fetch(instanceUrl, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                },
                body: JSON.stringify({
                    url: url,
                    videoQuality: '720'
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.url || data.picker) {
                    return res.json(data);
                }
            }
        } catch (err) {
            continue;
        }
    }

    return res.status(502).json({ error: 'Video extraction server busy. Please re-try with a different link or platform.' });
});

module.exports = app;
