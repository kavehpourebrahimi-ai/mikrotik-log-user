# VMS Mobile Bridge

A small service that runs **on the Windows VMS server** and gives you a
mobile-friendly web app to:

- see every camera configured in the VMS,
- watch each camera **live** (RTSP is pulled by the server and repackaged as HLS),
- browse and play **recorded video by date/time** straight from the `.vdo` archive.

The phone only ever talks to this server. Camera IPs and passwords stay on the
server (they are read from the VMS MySQL database, never re-entered).

```
 phone ── HTTP/HLS ──►  bridge (this app, on the VMS server)  ──► cameras (RTSP)
                                     └──► E:\VMS\Record (.vdo/.idx/.map archive)
```

## Requirements (on the Windows server)

1. **Python 3.9+** — https://www.python.org/downloads/windows/
2. **ffmpeg / ffprobe** — https://www.gyan.dev/ffmpeg/builds/
   - Download **ffmpeg-release-essentials.zip**, extract (e.g. to `C:\ffmpeg`),
     and either add `C:\ffmpeg\bin` to the system `PATH`, **or** set full paths
     in `config.ini`:
     ```
     [tools]
     ffmpeg_bin = C:\ffmpeg\bin\ffmpeg.exe
     ffprobe_bin = C:\ffmpeg\bin\ffprobe.exe
     ```
   - Verify in a new Command Prompt: `ffmpeg -version` and `ffprobe -version`
3. Python packages:
   ```
   pip install -r requirements.txt
   ```

## Setup

1. Copy the config and edit it:
   ```
   copy config.example.ini config.ini
   ```
   Check especially:
   - `[archive] record_root` — where recordings are stored (e.g. `E:\VMS\Record`)
   - `[db]` — MySQL host/port/user/password (defaults match the VMS install:
     `127.0.0.1:34176`, `root` / `root`, database `surveillancesystem`)

2. Find the correct RTSP URL for your cameras (Longse/FreeIP vary by model):
   ```
   python probe_rtsp.py
   python probe_one.py 192.168.21.5 --verbose
   ```
   Export camera user/password/IP from the VMS database:
   ```
   python export_cameras.py
   python export_cameras.py --ip 192.168.21.5
   python export_cameras.py --csv cameras.csv
   ```
   Copy the printed `rtsp_template = ...` line into `config.ini` under `[live]`.

3. Start the bridge:
   ```
   python app.py
   ```
   It listens on `http://0.0.0.0:8080` by default.

## Use it from a phone

- On the same LAN/VPN as the server, open:
  ```
  http://<server-ip>:8080/
  ```
  e.g. `http://192.168.21.197:8080/`
- To use it over the internet, port-forward **only** this port (8080) on the
  server to the outside — the cameras stay private behind the server.

## Notes

- **Live** and **playback** use `copy_codec=true` by default: the server only
  repackages HEVC (no re-encoding, low CPU). The phone decodes HEVC. iPhone /
  Safari usually works; some Android Chrome builds do not — then set
  `copy_codec=false` in `config.ini` (heavy server CPU).
- `GET /api/health` reports DB connectivity, camera count and whether the record
  root is visible.
- Temporary HLS/MP4 files are written under the system temp dir
  (`%TEMP%\vms_bridge`) and cleaned up / overwritten automatically.

## How the archive is read

The VMS stores, per camera per day:

```
<record_root>/<GUID>/<YYYY-MM-DD>/<GUID>.map           daily segment index
<record_root>/<GUID>/<YYYY-MM-DD>/<HH-MM-SS>/<GUID>_<N>.vdo   raw HEVC stream
```

`archive.py` parses the `.map` to list segments with begin/end times, and
`streams.py` remuxes the raw HEVC `.vdo` to MP4 with ffmpeg. No proprietary
network protocol is involved.
