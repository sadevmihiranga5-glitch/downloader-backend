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
    quality = data.get('quality', '1080')        # '1080', '720', '360'

    # Temp Folder එක සාදා ගැනීම
    temp_dir = tempfile.mkdtemp()
    out_template = os.path.join(temp_dir, '%(title)s.%(ext)s')

    # Base yt-dlp Options
    ydl_opts = {
        'outtmpl': out_template,
        'quiet': True,
        'no_warnings': True,
    }

    # YouTube Bot Protection Bypass
    if "youtube.com" in video_url or "youtu.be" in video_url:
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'ios', 'mweb']}}
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'

    # 1. MP3 Request එකක් නම් FFmpeg මගින් Convert කරයි
    if requested_format == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    # 2. Video (MP4) Request එකක් නම් (1080p, 720p, 360p) FFmpeg මගින් Merge කරයි
    else:
        if quality == '1080':
            ydl_opts['format'] = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best'
        elif quality == '720':
            ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best'
        else: # 360p
            ydl_opts['format'] = 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best'
        
        ydl_opts['merge_output_format'] = 'mp4'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'media')

            # Download වූ file එක සොයාගෙන Client ට Send කිරීම
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                if requested_format == 'mp3' and file.endswith('.mp3'):
                    return send_file(file_path, mimetype='audio/mpeg', as_attachment=True, download_name=f"{title}.mp3")
                elif requested_format != 'mp3' and file.endswith('.mp4'):
                    return send_file(file_path, mimetype='video/mp4', as_attachment=True, download_name=f"{title}.mp4")

            return jsonify({'status': 'error', 'message': 'File processing failed.'}), 500

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
