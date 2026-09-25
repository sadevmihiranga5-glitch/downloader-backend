const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');

const app = express();
app.use(cors());
app.use(express.json());

app.post('/api/download', async (req, res) => {
    const { url } = req.body;
    if (!url) return res.status(400).json({ status: 'error', text: 'URL required' });

    try {
        const response = await fetch('https://cobalt-api.kwi.li/', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                videoQuality: '720'
            })
        });

        const data = await response.json();
        return res.json(data);
    } catch (error) {
        return res.status(500).json({ status: 'error', text: 'Server error: ' + error.message });
    }
});

module.exports = app;
