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
    if (!url) return res.status(400).json({ error: 'URL එක අවශ්‍යයි' });

    // ඔයා Copy කරගත් API Key එක මෙතැනට දාන්න
    const apiKey = 'HYmMPMuoHjK';

    try {
        const apiUrl = `https://api.zm.io.vn/v1/social/autolink?apikey=${apiKey}&url=${encodeURIComponent(url)}`;
        
        const response = await fetch(apiUrl, {
            method: 'GET',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
        });

        const data = await response.json();

        // Direct Video Link එක Extract කිරීම
        let downloadUrl = null;
        if (data && data.data && data.data.url) {
            downloadUrl = data.data.url;
        } else if (data && data.url) {
            downloadUrl = data.url;
        } else if (data && data.medias && data.medias[0]) {
            downloadUrl = data.medias[0].url;
        }

        if (downloadUrl) {
            return res.json({
                url: downloadUrl,
                filename: 'video_download',
                type: 'video'
            });
        } else {
            return res.status(400).json({ error: 'Video extract කරගැනීමට නොහැකි විය. වෙනත් Link එකක් උත්සාහ කරන්න.' });
        }

    } catch (error) {
        return res.status(500).json({ error: 'Server එකෙහි දෝෂයක්. කරුණාකර නැවත උත්සාහ කරන්න.' });
    }
});

module.exports = app;
