from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'URL එක ඇතුළත් කරන්න'}), 400

    # YouTube Block වීම වැළැක්වීමට යොදන විශේෂ Options
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'extract_flat': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            medias = []
            formats = info.get('formats', [])
            
            for f in formats:
                # Video සහ Audio දෙකම තියෙන MP4 Formats විතරක් තෝරා ගැනීම
                if f.get('vcodec') != 'none' and f.get('url'):
                    quality_label = f.get('format_note') or (f"{f.get('height')}p" if f.get('height') else 'HD Quality')
                    medias.append({
                        'url': f.get('url'),
                        'quality': quality_label,
                        'extension': f.get('ext', 'mp4')
                    })

            # Formats ලැයිස්තුව හිස් නම් Best Direct Link එක යැවීම
            if not medias and info.get('url'):
                medias.append({
                    'url': info.get('url'),
                    'quality': 'Default Quality',
                    'extension': 'mp4'
                })

            return jsonify({
                'title': info.get('title', 'YouTube Video'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': str(info.get('duration', '00:00')),
                'medias': medias
            })

    except Exception as e:
        print("Error:", str(e))
        return jsonify({'error': 'YouTube වීඩියෝව ලබා ගැනීමට නොහැකි විය: ' + str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
