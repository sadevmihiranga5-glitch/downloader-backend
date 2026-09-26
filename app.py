import os
import yt_dlp
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/download', methods=['POST'])
def download_media():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'status': 'error', 'message': 'URL is required'}), 400

    video_url = data.get('url')
    requested_format = data.get('format', 'mp4')

    if requested_format == 'mp3':
        fmt = 'bestaudio/best'
    else:
        fmt = 'best'

    ydl_opts = {
        'format': fmt,
        'quiet': True,
        'no_warnings': True,
        # iOS / Android Web client එකෙන් Bot Block එක සම්පූර්ණයෙන්ම bypass කරයි
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'mweb']
            }
        },
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    }

    # cookies.txt එකක් ඇත්නම් පමණක් එය භාවිතා කරයි
    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            download_url = info.get('url')
            
            if not download_url and 'formats' in info:
                for f in reversed(info['formats']):
                    if f.get('url'):
                        download_url = f['url']
                        break

            if not download_url:
                return jsonify({'status': 'error', 'message': 'Direct stream link not available.'}), 400

            return jsonify({
                'status': 'success',
                'title': info.get('title', 'Downloaded Media'),
                'thumbnail': info.get('thumbnail', ''),
                'download_url': download_url
            })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
