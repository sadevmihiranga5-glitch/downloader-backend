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

YTDL_BASE_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "extract_flat": False,
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
        return jsonify({"status": "error", "message": "URL lagel."}), 400

    try:
        source_url = validate_source_url(data["url"].strip())
    except ValueError as error:
        return jsonify({"status": "error", "message": str(error)}), 400

    output_format = str(data.get("format", "mp4")).lower()
    if output_format not in ("mp4", "mp3"):
        return jsonify({"status": "error", "message": "Format mp4 kinva mp3 asava."}), 400

    try:
        info = extract_info(source_url)
    except yt_dlp.utils.DownloadError as error:
        return jsonify({"status": "error", "message": str(error)}), 422
    except Exception:
        app.logger.exception("Media information extraction failed")
        return jsonify({"status": "error", "message": "Video info milali nahi."}), 502

    title = str(info.get("title") or "video")
    thumbnail = info.get("thumbnail") or ""
    raw_formats = info.get("formats", [])

    medias = []

    # MP3 audio option
    if output_format == "mp3":
        best_audio = None
        for f in reversed(raw_formats):
            if f.get("acodec") != "none" and f.get("url"):
                best_audio = f.get("url")
                break
        
        if not best_audio:
            best_audio = info.get("url")

        media = {
            "url": best_audio,
            "type": "audio",
            "extension": "mp3",
            "quality": "MP3 320 kbps",
            "mimeType": "audio/mpeg",
        }
        return jsonify({"status": "success", "title": title, "thumbnail": thumbnail, "medias": [media]})

    # MP4 Video Option (Resolution filtering as requested earlier)
    available_items = []
    for f in raw_formats:
        url = f.get("url")
        if not url:
            continue

        height = f.get("height") or 0
        vcodec = f.get("vcodec")
        format_id = str(f.get("format_id") or "").lower()
        format_note = str(f.get("format_note") or "").upper()

        if "hd" in format_id or "hd" in format_note:
            height = 1080 if height == 0 else height
        elif "sd" in format_id or "sd" in format_note:
            height = 480 if height == 0 else height

        if height > 0 or vcodec not in (None, "none"):
            available_items.append({
                "url": url,
                "height": height,
                "ext": f.get("ext", "mp4")
            })

    if available_items:
        available_items.sort(key=lambda x: x["height"], reverse=True)
        max_height = available_items[0]["height"]

        target_heights = []
        if max_height > 1080:
            target_heights = [1080, 480]
        elif max_height > 0:
            target_heights = [max_height]

        seen_heights = set()
        for h in target_heights:
            match_item = next((item for item in available_items if item["height"] == h), None)
            if not match_item and available_items:
                match_item = available_items[0]

            if match_item and match_item["url"] not in seen_heights:
                seen_heights.add(match_item["url"])
                q_label = f"MP4 ({match_item['height']}p)" if match_item['height'] > 0 else "MP4 HD Quality"
                medias.append({
                    "url": match_item["url"],
                    "type": "video",
                    "extension": match_item["ext"],
                    "quality": q_label,
                    "height": match_item["height"]
                })

    if not medias and info.get("url"):
        medias.append({
            "url": info.get("url"),
            "type": "video",
            "extension": "mp4",
            "quality": "Best Available MP4",
            "height": info.get("height", 720)
        })

    return jsonify({
        "status": "success",
        "title": title,
        "thumbnail": thumbnail,
        "medias": medias,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))

YTDL_BASE_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    # YouTube Bot Block එක මඟහැරීමට Client Type එක iOS/Android ලෙස වෙනස් කිරීම
    "extractor_args": {
        "youtube": {
            "player_client": ["ios", "android"]
        }
    },
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-us,en;q=0.5",
    }
}
