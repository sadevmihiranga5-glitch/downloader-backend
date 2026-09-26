const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');

const app = express();

// CORS Issue එක විසඳීමට
app.use(cors({
    origin: '*',
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type']
}));

app.use(express.json());

const cobaltInstances = [
    'https://cobalt-api.kwi.li/',
    'https://cobalt.hyper.lol/'
];

app.post('/api/download', async (req, res) => {
    const { url } = req.body;
    if (!url) return res.status(400).json({ error: 'URL is required' });

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
                return res.json(data);
            }
        } catch (err) {
            continue;
        }
    }

    return res.status(502).json({ error: 'All backend instances failed.' });
});

module.exports = app;
