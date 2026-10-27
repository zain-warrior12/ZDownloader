# ZDownloader — YouTube & Instagram Media Downloader

A starter full-stack project using Python, Flask, yt-dlp, FFmpeg, HTML, CSS and JavaScript.

## Requirements

- Python 3.10+
- FFmpeg and ffprobe available on PATH (Docker installs FFmpeg for deployment)
- Internet access
- Download only media you own or are authorized to save. Respect platform terms and copyright.

## Run on Windows

Open PowerShell in this project folder:

```powershell
py -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser. The terminal should show Flask starting and a local address. **Do not paste JavaScript into the terminal**; the browser code is in `static/script.js`.

Check that FFmpeg is available:

```powershell
ffmpeg -version
ffprobe -version
```

If either command is not recognized, install FFmpeg and add its `bin` directory to your Windows PATH, then reopen the terminal.

## API endpoints

- `GET /api/health` — health check
- `POST /api/info` — JSON body: `{"url":"https://..."}`
- `POST /api/download` — JSON body: `{"url":"https://...","quality":"720","mode":"video"}`

Quality options: `360`, `480`, `720`, `1080`, `best`. Mode options: `video`, `audio`.

The frontend uses `const API = "";`, so the same-origin API works both locally and after deployment.

## Deploy using Docker

This project includes a Dockerfile with FFmpeg and Node.js installed. Push the project to GitHub, then deploy it to a Docker-capable host. Render's free-tier availability, disk, memory, execution time and bandwidth limits can change; verify the provider's current terms before relying on it.

For a local Docker test:

```bash
docker build -t zdownloader .
docker run --rm -p 5000:5000 zdownloader
```

Then visit http://127.0.0.1:5000.

## Limitations and production notes

- Public links only; private/login-protected media may not work.
- Platform extractors can break when sites change.
- This starter limits downloads to 100 MB and handles one synchronous request per worker. Large files or multiple users may exceed free hosting limits.
- A reverse proxy, job queue, per-IP rate limiting, concurrency controls, robust cleanup, monitoring and abuse prevention should be added before public use.
- `max_filesize` is a best-effort yt-dlp setting, not a complete resource-isolation boundary.
- The current audio mode downloads the source audio format; it does not convert it to MP3.
- No login cookies or credentials are collected or stored.


## Troubleshooting: download fails but preview works

1. Look at the same terminal where `python app.py` is running. The backend logs the detailed yt-dlp error there.
2. Check FFmpeg:
   ```powershell
   ffmpeg -version
   ffprobe -version
   ```
   If Windows says the command is not recognized, install FFmpeg, add its `bin` folder to PATH, and restart VS Code/PowerShell.
3. Update yt-dlp:
   ```powershell
   python -m pip install --upgrade "yt-dlp[default]"
   ```
4. Try **Best available** or 360p. A source may not provide every requested resolution.
5. Some YouTube links temporarily require verification or may be restricted. This app intentionally does not collect login cookies or passwords.

The UI now shows a more specific error instead of always displaying the same generic message. Do not publish the service without rate limiting and resource controls.


## Recent UI refinements

- The preview card stays hidden until a URL is previewed; the thumbnail uses an aesthetic placeholder instead of a broken-image icon.
- The URL input triggers a debounced automatic preview after a complete HTTPS URL is pasted or entered. The Preview button remains available as a manual fallback.
- Download filenames are prefixed with `zdownload-`.
- The dark theme has subtle violet/blue glow refinements.
