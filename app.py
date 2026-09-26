import os
import tempfile
import yt_dlp
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/download', methods=['POST'])
def download_media():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'status': 'error', 'message': 'URL is required'}), 400

    video_url = data.get('url')
    requested_format = data.get('format', 'mp4') # 'mp4' හෝ 'mp3'
    quality = data.get('quality', '720')          # '360' හෝ '720'

    # 1. Genuine MP3 Extraction Logic (Using FFmpeg Server-side)
    if requested_format == 'mp3':
        temp_dir = tempfile.mkdtemp()
        out_template = os.path.join(temp_dir, '%(title)s.%(ext)s')

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        if "youtube.com" in video_url or "youtu.be" in video_url:
            ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'ios', 'mweb']}}
            if os.path.exists('cookies.txt'):
                ydl_opts['cookiefile'] = 'cookies.txt'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                title = info.get('title', 'audio')

                # Download වුණු Temp folder එකෙන් පරිවර්තනය වූ MP3 file එක සොයාගැනීම
                for file in os.listdir(temp_dir):
                    if file.endswith('.mp3'):
                        file_path = os.path.join(temp_dir, file)
                        return send_file(file_path, as_attachment=True, download_name=f"{title}.mp3")

                return jsonify({'status': 'error', 'message': 'MP3 conversion failed.'}), 500

        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # 2. Direct MP4 Video Stream Extraction Logic
    else:
        if quality == '360':
            fmt = 'best[height<=360][vcodec!=none][acodec!=none]/best[height<=360]/best'
        elif quality == '720':
            fmt = 'best[height<=720][vcodec!=none][acodec!=none]/best[height<=720]/best'
        else:
            fmt = 'best[vcodec!=none][acodec!=none]/best'

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

                if not download_url and 'formats' in info:
                    for f in reversed(info['formats']):
                        if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                            download_url = f['url']
                            break

                if not download_url and 'formats' in info:
                    for f in reversed(info['formats']):
                        if f.get('url'):
                            download_url = f['url']
                            break

                if not download_url:
                    return jsonify({'status': 'error', 'message': 'Direct stream link not found.'}), 400

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
