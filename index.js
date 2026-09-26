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

    // Official Cobalt Main API Instance
    const instances = [
        'https://api.cobalt.tools',
        'https://cobalt-api.kwi.li'
    ];

    for (const instance of instances) {
        try {
            const response = await fetch(instance, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                },
                body: JSON.stringify({
                    url: url,
                    videoQuality: '720',
                    downloadMode: 'auto'
                })
            });

            const data = await response.json();

            if (data && (data.url || data.picker)) {
                return res.json({
                    url: data.url || (data.picker && data.picker[0] ? data.picker[0].url : null),
                    filename: 'video_download',
                    type: 'video'
                });
            }
        } catch (e) {
            continue;
        }
    }

    return res.status(500).json({ error: 'Extraction failed. Try another link.' });
});

module.exports = app;
