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

    // 🔴 ඔයාගේ ZM API Key එක මෙතැනට දාන්න
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
        console.log("ZM API Response:", JSON.stringify(data)); // Vercel Logs වල බලන්න

        // Deep extraction logic for multiple response patterns
        let downloadUrl = null;

        if (data) {
            if (typeof data === 'string' && data.startsWith('http')) {
                downloadUrl = data;
            } else if (data.data) {
                if (typeof data.data === 'string' && data.data.startsWith('http')) downloadUrl = data.data;
                else if (data.data.url) downloadUrl = data.data.url;
                else if (Array.isArray(data.data.medias) && data.data.medias[0]) downloadUrl = data.data.medias[0].url;
                else if (Array.isArray(data.data) && data.data[0] && data.data[0].url) downloadUrl = data.data[0].url;
            } else if (data.url) {
                downloadUrl = data.url;
            } else if (Array.isArray(data.medias) && data.medias[0]) {
                downloadUrl = data.medias[0].url;
            }
        }

        if (downloadUrl) {
            return res.json({
                url: downloadUrl,
                filename: 'video_download',
                type: 'video'
            });
        } else {
            return res.status(400).json({ error: 'Video extraction failed. Try another link.' });
        }

    } catch (error) {
        return res.status(500).json({ error: 'Server timeout/error. Try again.' });
    }
});

module.exports = app;
