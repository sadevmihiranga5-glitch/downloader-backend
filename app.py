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

    # Format selection - FB, IG සහ YT සදහා
    if requested_format == 'mp3':
        fmt = 'bestaudio/best'
    else:
        # Audio + Video එකට තියෙන MP4 එකක්, නැත්නම් වෙනත් ඕනෑම workable direct format එකක් ගනී
        fmt = 'best[ext=mp4][vcodec!=none][acodec!=none]/best[vcodec!=none][acodec!=none]/best'

    ydl_opts = {
        'format': fmt,
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    # YouTube සඳහා පමණක් cookies සහ extractor args සෙට් කිරීම
    if "youtube.com" in video_url or "youtu.be" in video_url:
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'ios', 'mweb']}}
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            download_url = info.get('url')

            # Direct link එකක් නැත්නම් formats ලැයිස්තුවෙන් Audio + Video තියෙන හොඳම එක සොයයි
            if not download_url and 'formats' in info:
                for f in reversed(info['formats']):
                    if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        download_url = f['url']
                        break
                
                # එසේ නොමැති නම් ඕනෑම direct link එකක් තෝරා ගනී
                if not download_url:
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
