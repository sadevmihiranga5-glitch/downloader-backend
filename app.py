import os
import re
from urllib.parse import urlparse

import yt_dlp
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
CORS(app, resources={r"/api/*": {"origins": "*"}})

ALLOWED_HOSTS = (
    "youtube.com",
    "youtu.be",
    "facebook.com",
    "fb.watch",
    "instagram.com",
    "instagr.am",
)

# YouTube සහ Facebook Block වීම වැළැක්වීමට User-Agent Headers
YTDL_BASE_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-us,en;q=0.5",
    }
}


def validate_source_url(raw_url):
    parsed = urlparse(raw_url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not any(
        hostname == domain or hostname.endswith("." + domain)
        for domain in ALLOWED_HOSTS
    ):
        raise ValueError("Use a public YouTube, Facebook, or Instagram video URL.")
    return raw_url


def extract_info(source_url):
    options = YTDL_BASE_OPTIONS.copy()
    options["skip_download"] = True
    
    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(source_url, download=False)
    if not isinstance(info, dict):
        raise ValueError("No video information was returned.")
    return info


@app.get("/")
def health_check():
    return jsonify({"status": "running", "message": "DownMaster Flask backend active"})


@app.post("/api/download")
def get_download_options():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("url"), str):
        return jsonify({"status": "error", "message": "URL එක ඇතුළත් කරන්න."}), 400

    try:
        source_url = validate_source_url(data["url"].strip())
    except ValueError as error:
        return jsonify({"status": "error", "message": str(error)}), 400

    output_format = str(data.get("format", "mp4")).lower()
    if output_format not in ("mp4", "mp3"):
        return jsonify({"status": "error", "message": "Format එක mp4 හෝ mp3 විය යුතුය."}), 400

    try:
        info = extract_info(source_url)
    except yt_dlp.utils.DownloadError as error:
        return jsonify({"status": "error", "message": str(error)}), 422
    except Exception:
        app.logger.exception("Media information extraction failed")
        return jsonify({"status": "error", "message": "වීඩියෝ තොරතුරු ලබා ගැනීමට නොහැකි විය."}), 502

    title = str(info.get("title") or "video")
    thumbnail = info.get("thumbnail") or ""
    formats = info.get("formats", [])

    medias = []

    # --- MP3 Select කළ විට ---
    if output_format == "mp3":
        best_audio = None
        for f in reversed(formats):
            if f.get("acodec") != "none" and f.get("url"):
                best_audio = f.get("url")
                break
        
        if not best_audio:
            best_audio = info.get("url")

        media = {
            "url": best_audio,
            "type": "audio",
            "extension": "mp3",
            "quality": "Direct Audio Stream",
            "mimeType": "audio/mpeg",
        }
        return jsonify({"status": "success", "title": title, "thumbnail": thumbnail, "medias": [media]})

    # --- MP4 (Facebook, YouTube, Instagram) Select කළ විට ---
    seen_urls = set()
    seen_qualities = set()

    for f in formats:
        url = f.get("url")
        if not url or url in seen_urls:
            continue

        vcodec = f.get("vcodec")
        format_id = str(f.get("format_id") or "").lower()
        format_note = str(f.get("format_note") or "").upper()
        height = f.get("height") or 0

        # Facebook HD/SD Direct Links අඳුරගැනීම
        quality_label = None
        if "hd" in format_id or "hd" in format_note:
            quality_label = "FB HD Quality (1080p/720p)"
        elif "sd" in format_id or "sd" in format_note:
            quality_label = "FB SD Quality (360p/480p)"
        elif height > 0:
            quality_label = f"MP4 ({height}p)"
        elif vcodec not in (None, "none"):
            quality_label = "MP4 Direct Video"

        if quality_label and quality_label not in seen_qualities:
            seen_urls.add(url)
            seen_qualities.add(quality_label)
            medias.append({
                "url": url,
                "type": "video",
                "extension": f.get("ext", "mp4"),
                "quality": quality_label,
                "height": height
            })

    # Formats මුකුත්ම හමු නොවුණොත් Direct URL එක ලබාදීම
    if not medias and info.get("url"):
        medias.append({
            "url": info.get("url"),
            "type": "video",
            "extension": "mp4",
            "quality": "Direct HD Quality",
            "height": info.get("height", 720)
        })

    # Height එක අනුව වැඩිම එක උඩට එනසේ සකස් කිරීම
    medias.sort(key=lambda x: x.get("height", 0), reverse=True)

    return jsonify({
        "status": "success",
        "title": title,
        "thumbnail": thumbnail,
        "medias": medias,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
