import os
import requests
import yt_dlp
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 🔑 ShrinkMe.io API Key & Endpoint Integration
SHORTENER_API_KEY = "595b9dd64631ced1d929da59358f6c2302382586"
SHORTENER_API_URL = "https://shrinkme.io/api"

def shorten_url(long_url):
    try:
        params = {
            'api': SHORTENER_API_KEY,
            'url': long_url
        }
        response = requests.get(SHORTENER_API_URL, params=params, timeout=10)
        data = response.json()
        
        if data.get('status') == 'success':
            return data.get('shortenedUrl')
        else:
            print("Shortener Status Error:", data)
            return long_url
    except Exception as e:
        print("Shortener Request Error:", e)
        return long_url

@app.route('/api/download', methods=['POST'])
def download_media():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'status': 'error', 'message': 'URL is required'}), 400

    video_url = data.get('url')
    requested_format = data.get('format', 'mp4')
    quality = data.get('quality', '720')

    # Automatic Resolution Fallback
    if requested_format == 'mp3':
        fmt = 'bestaudio/best'
    else:
        fmt = f'best[height<={quality}][vcodec!=none][acodec!=none]/bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best'

    ydl_opts = {
        'format': fmt,
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    if "youtube.com" in video_url or "youtu.be" in video_url:
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'ios', 'mweb']}}
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            download_url = info.get('url')

            # Double Check Stream Fallback
            if not download_url and 'formats' in info:
                for f in reversed(info['formats']):
                    if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        download_url = f['url']
                        break
                
                if not download_url:
                    for f in reversed(info['formats']):
                        if f.get('url'):
                            download_url = f['url']
                            break

            if not download_url:
                return jsonify({'status': 'error', 'message': 'Direct stream link not found for this video.'}), 400

            # Direct Download Link එක ShrinkMe.io හරහා Short කිරීම
            final_monetized_link = shorten_url(download_url)

            return jsonify({
                'status': 'success',
                'title': info.get('title', 'Downloaded Media'),
                'thumbnail': info.get('thumbnail', ''),
                'download_url': final_monetized_link
            })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
