# VMS Mobile Bridge

**Simple goal:** same as the Windows VMS client, in a browser.

```
Browser  →  this app (on the VMS server)  →  MySQL + E:\VMS\Record + cameras (RTSP)
```

See **SIMPLE.md** (Persian) for the short setup guide.

## Quick start (Windows server)

1. Install Python 3.9+ and ffmpeg (`C:\ffmpeg\bin`)
2. Double-click `install.bat`
3. Edit `config.ini` (paths below)
4. Double-click `start.bat`
5. Open `http://<server-ip>:8080/`

```ini
[tools]
ffmpeg_bin = C:\ffmpeg\bin\ffmpeg.exe
ffprobe_bin = C:\ffmpeg\bin\ffprobe.exe
[archive]
record_root = E:\VMS\Record
[live]
rtsp_template = rtsp://{user}:{password}@{ip}:{port}/0
rtsp_port = 554
copy_codec = true
```

`copy_codec = true` = server only repackages video (low CPU). The browser decodes HEVC.

## What it does

- Lists cameras from `surveillancesystem` MySQL (same DB as VMS)
- Live: pulls RTSP using stored credentials, serves HLS to the browser
- Playback: reads `.vdo` archive, remuxes to MP4 (no re-encode by default)
- Auto-finds the correct RTSP path per camera (`/0`, `/11`, …)

## Requirements

1. **Python 3.9+**
2. **ffmpeg** — only for repackaging streams, not heavy transcoding
3. `pip install -r requirements.txt` (or run `install.bat`)

## Detailed docs

Older step-by-step notes are below. Prefer **SIMPLE.md** for day-to-day use.

---
