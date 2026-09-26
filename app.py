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

    # Base settings
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
    }

    # Cookies ෆයිල් එකක් තිබේ නම් පමණක් එකතු කරයි
    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'

    try:
        # 1. පළමු උත්සාහය: සාමාන්‍ය විදිහට Extract කිරීම
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        download_url = info.get('url')

        # 2. Direct URL එකක් නැතිනම්, Formats ලැයිස්තුවෙන් URL එකක් සෙවීම
        if not download_url and 'formats' in info:
            # MP3 නම් හොඳම Audio එක සොයයි
            if requested_format == 'mp3':
                for f in reversed(info['formats']):
                    if f.get('url') and f.get('vcodec') == 'none':
                        download_url = f['url']
                        break
            else:
                # Video නම් Audio + Video දෙකම තියෙන direct stream එකක් සොයයි
                for f in reversed(info['formats']):
                    if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        download_url = f['url']
                        break

            # තවමත් හමු නොවුණි නම් ඕනෑම direct link එකක් තෝරාගනී
            if not download_url:
                for f in reversed(info['formats']):
                    if f.get('url'):
                        download_url = f['url']
                        break

        if not download_url:
            return jsonify({'status': 'error', 'message': 'Direct download link could not be generated.'}), 400

        return jsonify({
            'status': 'success',
            'title': info.get('title', 'Downloaded Media'),
            'thumbnail': info.get('thumbnail', ''),
            'download_url': download_url
        })

    except Exception as e:
        # 3. යම් හෙයකින් Bot Block වී ඇතිනම් Android client මගින් Fallback කිරීම
        try:
            ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                download_url = info.get('url')
                
                if not download_url and 'formats' in info:
                    for f in reversed(info['formats']):
                        if f.get('url'):
                            download_url = f['url']
                            break

                if download_url:
                    return jsonify({
                        'status': 'success',
                        'title': info.get('title', 'Downloaded Media'),
                        'thumbnail': info.get('thumbnail', ''),
                        'download_url': download_url
                    })
        except Exception:
            pass

        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
