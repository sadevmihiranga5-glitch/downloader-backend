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

    try {
        const response = await fetch(`https://instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com/index?url=${encodeURIComponent(url)}`, {
            method: 'GET',
            headers: {
                'x-rapidapi-key': 'f2e17beecamshce51f67bc096864p12a822jsnf7bddc705140',
                'x-rapidapi-host': 'instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com'
            }
        });

        const data = await response.json();

        // Extract direct download link
        let downloadUrl = null;
        if (data && data.media) {
            downloadUrl = data.media;
        } else if (data && data[0] && data[0].media) {
            downloadUrl = data[0].media;
        } else if (data && data.url) {
            downloadUrl = data.url;
        }

        if (downloadUrl) {
            return res.json({
                url: downloadUrl,
                filename: 'video_download',
                type: 'video'
            });
        } else {
            return res.status(400).json({ error: 'Video Link එක extract කරගැනීමට නොහැකි විය. වෙනත් link එකක් උත්සාහ කරන්න.' });
        }

    } catch (error) {
        return res.status(500).json({ error: 'Server එකෙහි දෝෂයක්. කරුණාකර නැවත උත්සාහ කරන්න.' });
    }
});

module.exports = app;
