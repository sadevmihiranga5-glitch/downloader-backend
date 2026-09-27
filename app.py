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
    "check_formats": False,
    "extractor_args": {
        "youtube": {
            "player_client": ["ios", "android"]
        },
        "instagram": {
            "app_version": "269.0.0.18.75"
        }
    },
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Sec-Fetch-Mode": "navigate",
    }
}

if os.path.exists("cookies.txt"):
    YTDL_BASE_OPTIONS["cookiefile"] = "cookies.txt"


def validate_source_url(raw_url):
    parsed = urlparse(raw_url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not any(
        hostname == domain or hostname.endswith("." + domain)
        for domain in ALLOWED_HOSTS
    ):
        raise ValueError("Please provide a valid public YouTube, Facebook, or Instagram URL.")
    return raw_url


def extract_info(source_url):
    options = YTDL_BASE_OPTIONS.copy()
    options["skip_download"] = True
    
    if "facebook.com" in source_url or "fb.watch" in source_url:
        options["http_headers"] = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(source_url, download=False)
    if not isinstance(info, dict):
        raise ValueError("Failed to retrieve media details from the provided URL.")
    return info


@app.get("/")
def health_check():
    return jsonify({"status": "running", "message": "DownMaster Flask backend active"})


@app.post("/api/download")
def get_download_options():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("url"), str):
        return jsonify({"status": "error", "message": "URL parameter is required."}), 400

    try:
        source_url = validate_source_url(data["url"].strip())
    except ValueError as error:
        return jsonify({"status": "error", "message": str(error)}), 400

    raw_format = data.get("format") or data.get("output_format") or "mp4"
    output_format = str(raw_format).strip().lower()

    if output_format not in ("mp4", "mp3"):
        return jsonify({"status": "error", "message": "Invalid format requested. Allowed formats are 'mp4' or 'mp3'."}), 400

    try:
        info = extract_info(source_url)
    except yt_dlp.utils.DownloadError:
        return jsonify({"status": "error", "message": "Unable to fetch media. The content may be private or restricted."}), 422
    except Exception:
        app.logger.exception("Media information extraction failed")
        return jsonify({"status": "error", "message": "An error occurred while processing the video information."}), 502

    title = str(info.get("title") or "video")
    thumbnail = info.get("thumbnail") or ""
    raw_formats = info.get("formats", [])

    medias = []

    # --- 1. MP3 Audio Formats (3 Options) ---
    if output_format == "mp3":
        audio_streams = []
        for f in reversed(raw_formats):
            if f.get("acodec") != "none" and f.get("url"):
                audio_streams.append(f)

        if audio_streams:
            bitrates = [("320 kbps", 0), ("192 kbps", 1), ("128 kbps", -1)]
            for label, idx in bitrates:
                selected_stream = audio_streams[idx if abs(idx) < len(audio_streams) else 0]
                medias.append({
                    "url": selected_stream.get("url"),
                    "type": "audio",
                    "extension": "mp3",
                    "quality": f"MP3 Audio ({label})",
                    "mimeType": "audio/mpeg"
                })
        else:
            default_url = info.get("url")
            medias.append({
                "url": default_url,
                "type": "audio",
                "extension": "mp3",
                "quality": "MP3 High Quality",
                "mimeType": "audio/mpeg"
            })

        return jsonify({"status": "success", "title": title, "thumbnail": thumbnail, "medias": medias})

    # --- 2. MP4 Video Formats (1080p, Max Quality & 480p Logic) ---
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

        if height > 0 or vcodec not in (None, "none") or "fb" in source_url:
            available_items.append({
                "url": url,
                "height": height,
                "ext": f.get("ext", "mp4")
            })

    if available_items:
        # Sort e toowgol height
        available_items.sort(key=lambda x: x["height"], reverse=True)
        max_height = available_items[0]["height"]

        # Logic no naamri maa nii:
        # 1. So max_height > 1080p: Heɓor [1080p, 480p]
        # 2. So max_height <= 1080p: Heɓor [max_height, 480p]
        target_heights = []
        if max_height > 1080:
            target_heights = [1080, 480]
        else:
            target_heights = [max_height]
            if max_height != 480:
                target_heights.append(480)

        seen_urls = set()
        for target in target_heights:
            # Ɓeeɗoo ko ƴeewtat ko ɓuri ɓadaade target height o
            closest_item = min(available_items, key=lambda x: abs(x["height"] - target) if x["height"] > 0 else 9999)
            if closest_item["url"] not in seen_urls:
                seen_urls.add(closest_item["url"])
                q_label = f"MP4 ({closest_item['height']}p)" if closest_item['height'] > 0 else "MP4 HD"
                medias.append({
                    "url": closest_item["url"],
                    "type": "video",
                    "extension": closest_item["ext"],
                    "quality": q_label,
                    "height": closest_item["height"]
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
