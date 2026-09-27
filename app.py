import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests
import yt_dlp
from flask import Flask, jsonify, request, send_file, url_for
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

# YouTube Block වීම වැළැක්වීමට විශේෂ Headers
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

def detected_video_heights(info):
    heights = set()
    for item in info.get("formats", []):
        if not isinstance(item, dict) or item.get("vcodec") in (None, "none"):
            continue

        height = item.get("height")
        if not height:
            resolution = str(item.get("resolution") or "")
            match = re.search(r"\d{2,5}x(\d{2,5})", resolution)
            height = match.group(1) if match else None

        try:
            height = int(height)
        except (TypeError, ValueError):
            continue
        if height > 0:
            heights.add(height)

    if not heights and info.get("height"):
        try:
            heights.add(int(info["height"]))
        except (TypeError, ValueError):
            pass

    return heights


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


def download_file_url(source_url, output_format, quality=None):
    return url_for(
        "download_file",
        _external=True,
        url=source_url,
        format=output_format,
        quality=quality,
    )


def media_option(source_url, quality):
    quality_label = f"MP4 ({quality}p)" if quality else "Best available MP4"
    raw_download_url = download_file_url(source_url, "mp4", quality)
    return {
        "url": raw_download_url,
        "type": "video",
        "extension": "mp4",
        "quality": quality_label,
        "height": quality,
        "mimeType": 'video/mp4; codecs="avc1, mp4a.40.2"',
        "audioQuality": "AUDIO_QUALITY_NORMAL",
        "audioSampleRate": 44100,
    }


@app.get("/")
def health_check():
    return jsonify({"status": "running", "message": "DownMaster Flask backend active"})


@app.post("/api/download")
def get_download_options():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("url"), str):
        return jsonify({"status": "error", "message": "URL is required."}), 400

    try:
        source_url = validate_source_url(data["url"].strip())
    except ValueError as error:
        return jsonify({"status": "error", "message": str(error)}), 400

    output_format = str(data.get("format", "mp4")).lower()
    if output_format not in ("mp4", "mp3"):
        return jsonify({"status": "error", "message": "Format must be mp4 or mp3."}), 400

    try:
        info = extract_info(source_url)
    except yt_dlp.utils.DownloadError as error:
        return jsonify({"status": "error", "message": str(error)}), 422
    except Exception:
        app.logger.exception("Media information extraction failed")
        return jsonify({"status": "error", "message": "Could not inspect this video."}), 502

    title = str(info.get("title") or "video")
    thumbnail = info.get("thumbnail") or ""

    if output_format == "mp3":
        raw_mp3_url = download_file_url(source_url, "mp3")
        media = {
            "url": raw_mp3_url,
            "type": "audio",
            "extension": "mp3",
            "quality": "MP3 320 kbps",
            "mimeType": "audio/mpeg",
        }
        return jsonify({"status": "success", "title": title, "thumbnail": thumbnail, "medias": [media]})

    available_heights = sorted(detected_video_heights(info))
    if not available_heights:
        # 480p default fallback එකක් ලබා දීම
        available_heights = [480]

    max_height = max(available_heights)

    # 🎯 ඔයා ඉල්ලපු Resolution Logic එක:
    if max_height > 1080:
        options_to_show = [1080, 480]
    else:
        options_to_show = [max_height]

    requested_quality = data.get("quality")
    if requested_quality is not None:
        try:
            requested_quality = int(requested_quality)
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": "Quality must be a number."}), 400

        if requested_quality not in available_heights:
            lower_options = [h for h in available_heights if h <= requested_quality]
            requested_quality = max(lower_options) if lower_options else min(available_heights)

        raw_download_url = download_file_url(source_url, "mp4", requested_quality)
        return jsonify({
            "status": "success",
            "title": title,
            "thumbnail": thumbnail,
            "format": "mp4",
            "quality": f"MP4 ({requested_quality}p)",
            "download_url": raw_download_url,
        })

    return jsonify({
        "status": "success",
        "title": title,
        "thumbnail": thumbnail,
        "medias": [media_option(source_url, q) for q in options_to_show],
    })


@app.get("/api/download-file")
def download_file():
    try:
        source_url = validate_source_url(request.args.get("url", ""))
    except ValueError as error:
        return jsonify({"status": "error", "message": str(error)}), 400

    output_format = request.args.get("format", "mp4").lower()
    quality = request.args.get("quality", type=int)
    if output_format not in ("mp4", "mp3"):
        return jsonify({"status": "error", "message": "Format must be mp4 or mp3."}), 400

    temp_dir = Path(tempfile.mkdtemp(prefix="downmaster-"))
    
    options = YTDL_BASE_OPTIONS.copy()
    options.update({
        "outtmpl": str(temp_dir / "%(title).100s.%(ext)s"),
        "overwrites": True,
    })

    if output_format == "mp3":
        options.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
        })
        expected_extension = ".mp3"
    else:
        if quality is None:
            format_selector = (
                "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                "best[ext=mp4]/bestvideo+bestaudio/best"
            )
        else:
            format_selector = (
                f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/"
                f"best[height<={quality}][ext=mp4]/"
                f"bestvideo[height<={quality}]+bestaudio/"
                f"best[height<={quality}]/bestvideo+bestaudio/best"
            )
        options.update({
            "format": format_selector,
            "merge_output_format": "mp4",
        })
        expected_extension = ".mp4"

    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([source_url])
        output_path = next(
            (path for path in temp_dir.iterdir() if path.suffix.lower() == expected_extension),
            None,
        )
        if output_path is None:
            raise RuntimeError("The requested output file was not created.")

        response = send_file(
            output_path,
            mimetype="audio/mpeg" if output_format == "mp3" else "video/mp4",
            as_attachment=True,
            download_name=output_path.name,
            conditional=False,
        )
        response.call_on_close(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        return response
    except yt_dlp.utils.DownloadError as error:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"status": "error", "message": str(error)}), 422
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        app.logger.exception("Media download failed")
        return jsonify({"status": "error", "message": "Could not create the requested file."}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
