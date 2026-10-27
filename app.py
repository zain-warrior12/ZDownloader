import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request, send_file
from yt_dlp import YoutubeDL

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # API requests should be tiny.
logging.basicConfig(level=logging.INFO)

ALLOWED_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
    "youtu.be", "instagram.com", "www.instagram.com"
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB starter-project safety limit.
TEMP_DIR = Path(tempfile.gettempdir()) / "media_downloader_jobs"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def validate_url(url):
    if not isinstance(url, str) or len(url) > 2048:
        return False
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        return (
            parsed.scheme == "https"
            and host in ALLOWED_HOSTS
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


def get_options():
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "retries": 1,
    }


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/info")
def video_info():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()

    if not validate_url(url):
        return jsonify({"error": "Please enter a valid HTTPS YouTube or Instagram URL."}), 400

    try:
        options = {**get_options(), "skip_download": True}
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        # Do not expose the full extractor response/cookies/technical metadata.
        return jsonify({
            "title": info.get("title") or "Untitled media",
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader") or info.get("channel") or "Unknown creator",
            "site": info.get("extractor_key") or "Media",
        })
    except Exception:
        app.logger.exception("Metadata extraction failed")
        return jsonify({
            "error": "Could not read this media. It may be private, unavailable, or blocked by the platform."
        }), 422


@app.post("/api/download")
def download_media():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    quality = str(data.get("quality", "720"))
    mode = str(data.get("mode", "video"))

    if not validate_url(url):
        return jsonify({"error": "Please enter a valid HTTPS YouTube or Instagram URL."}), 400
    if quality not in {"360", "480", "720", "1080", "best"}:
        return jsonify({"error": "Unsupported quality option."}), 400
    if mode not in {"video", "audio"}:
        return jsonify({"error": "Unsupported download mode."}), 400

    job_dir = Path(tempfile.mkdtemp(prefix="job_", dir=TEMP_DIR))
    height = "" if quality == "best" else f"[height<={quality}]"
    if mode == "audio":
        options = {
            **get_options(),
            "format": "bestaudio/best",
            "outtmpl": str(job_dir / "%(id)s.%(ext)s"),
            "max_filesize": MAX_FILE_SIZE,
        }
    else:
        options = {
            **get_options(),
            # Try a separate video+audio stream first, then a single-file format.
            "format": f"bestvideo{height}+bestaudio/best{height}/best",
            "outtmpl": str(job_dir / "%(id)s.%(ext)s"),
            "merge_output_format": "mp4",
            "max_filesize": MAX_FILE_SIZE,
            "format_sort": ["res", "ext:mp4:m4a"],
        }

    try:
        with YoutubeDL(options) as ydl:
            ydl.extract_info(url, download=True)

        candidates = [p for p in job_dir.iterdir() if p.is_file() and not p.name.endswith((".part", ".ytdl"))]
        if not candidates:
            raise RuntimeError("No output file was created.")

        output = max(candidates, key=lambda p: p.stat().st_size)
        if output.stat().st_size > MAX_FILE_SIZE:
            raise RuntimeError("The downloaded file exceeds this demo's 100 MB limit.")

        response = send_file(
            output,
            as_attachment=True,
            download_name=("zdownload-" + output.name if not output.name.lower().startswith("zdownload") else output.name),
            conditional=True,
        )
        response.call_on_close(lambda: shutil.rmtree(job_dir, ignore_errors=True))
        return response
    except Exception as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        app.logger.exception("Download failed")
        # Provide a useful diagnostic without returning a traceback or server paths.
        detail = str(exc).strip().replace("\\n", " ")
        if len(detail) > 220:
            detail = detail[:220] + "…"
        low = detail.lower()
        if "ffmpeg" in low or "postprocessing" in low:
            message = "FFmpeg is missing or not detected. Install FFmpeg, add its bin folder to PATH, restart the terminal, and run ffmpeg -version."
        elif "requested format is not available" in low or "format" in low and "not available" in low:
            message = "That quality is unavailable for this video. Try Best available or a lower quality."
        elif "maximum file size" in low or "filesize" in low and "exceed" in low:
            message = "This file exceeds the downloader's 100 MB limit. Try a shorter video."
        elif "sign in" in low or "bot" in low or "confirm you’re not a bot" in low or "confirm you are not a bot" in low:
            message = "YouTube requires verification for this request. Try a different public video later; do not enter account credentials into this app."
        else:
            message = "Download failed: " + (detail or "unknown yt-dlp error")
        return jsonify({"error": message}), 422


if __name__ == "__main__":
    # Local development only. Use Gunicorn/Docker in deployment.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
