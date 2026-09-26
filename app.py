import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)  # InfinityFree frontend එකට permission දීමට

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "running", "message": "yt-dlp Downloader Backend Active!"})

@app.route('/api/download', methods=['POST'])
def download():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "URL එක අවශ්‍යයි"}), 400

    video_url = data['url']

    ydl_opts = {
        'format': 'best[ext=mp4]/best',  # MP4 format එක තෝරාගැනීමට
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Direct Video URL එක සොයාගැනීම
            download_url = info.get('url')
            
            # Formats අතරින් Direct Link එක සෙවීම
            if not download_url and 'formats' in info:
                for fmt in reversed(info['formats']):
                    if fmt.get('url') and fmt.get('ext') == 'mp4':
                        download_url = fmt['url']
                        break

            if download_url:
                return jsonify({
                    "url": download_url,
                    "title": info.get('title', 'video_download'),
                    "filename": f"{info.get('title', 'video')}.mp4",
                    "type": "video"
                })
            else:
                return jsonify({"error": "Direct download link එක ලබාගත නොහැකි විය."}), 400

    except Exception as e:
        return jsonify({"error": f"Extraction Failed: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
