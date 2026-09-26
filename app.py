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

    # MP3 සහ MP4 සදහා නම්‍යශීලී (flexible) format selection
    if requested_format == 'mp3':
        # Audio විතරක් ගන්න බැරි වුණොත්, හොඳම වීඩියෝ එකෙන් Audio extract කරයි
        fmt = 'bestaudio/best'
    else:
        # MP4 නැතිනම් ඕනෑම හොඳම වීඩියෝ + ඕඩියෝ format එකක් තෝරාගනී
        fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

    ydl_opts = {
        'format': fmt,
        'quiet': True,
        'no_warnings': True,
        # YouTube 403 / Format unavailable එන එක වළක්වන ප්‍රධාන settings
        'extract_flat': False,
        'force_generic_extractor': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Direct link එක ලබා ගැනීම
            download_url = info.get('url')
            
            # Direct link එකක් නැතිනම් formats ලැයිස්තුවෙන් පළමු direct link එක ගැනීම
            if not download_url and 'formats' in info:
                for f in info['formats']:
                    if f.get('url'):
                        download_url = f['url']
                        break

            if not download_url:
                return jsonify({'status': 'error', 'message': 'Direct stream link not available for this video.'}), 400

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
