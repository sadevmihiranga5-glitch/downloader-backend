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
        // Facebook, YouTube, සහ Instagram සඳහා VKR Public Engine භාවිතය
        const apiUrl = `https://api.vkrdown.com/v1/main?url=${encodeURIComponent(url)}`;
        
        const response = await fetch(apiUrl, {
            method: 'GET',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
        });

        const data = await response.json();

        let downloadUrl = null;

        // Video Download Link එක සොයා ගැනීම
        if (data && data.data) {
            if (data.data.url) {
                downloadUrl = data.data.url;
            } else if (data.data.video) {
                downloadUrl = data.data.video;
            } else if (Array.isArray(data.data.download) && data.data.download.length > 0) {
                downloadUrl = data.data.download[0].url;
            } else if (Array.isArray(data.data.downloads) && data.data.downloads.length > 0) {
                downloadUrl = data.data.downloads[0].url;
            }
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
            return res.status(400).json({ error: 'Video එක extract කරගැනීමට නොහැකි විය. වෙනත් Link එකක් උත්සාහ කරන්න.' });
        }

    } catch (error) {
        return res.status(500).json({ error: 'Server එකෙහි දෝෂයක්. කරුණාකර නැවත උත්සාහ කරන්න.' });
    }
});

module.exports = app;
