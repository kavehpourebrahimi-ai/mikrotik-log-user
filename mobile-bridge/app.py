"""VMS Mobile Bridge - a small Flask service that runs on the Windows VMS server.

It exposes a mobile-friendly web app plus a JSON API so that a phone (on the
same LAN / VPN as the server, or via a port-forward to the server only) can:

  * list every camera that is configured in the VMS
  * watch each camera live       (RTSP pulled by the server -> HLS)
  * browse and play recordings   (.vdo archive on the server -> MP4/HLS)

The phone only ever talks to this server; camera IPs and credentials never
leave the server.
"""

from __future__ import annotations

import configparser
import os
import tempfile
import threading
import time

from flask import (Flask, jsonify, request, send_file, send_from_directory,
                   abort, Response)

import archive
import streams
from vms_db import VmsDatabase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg_path = os.environ.get("BRIDGE_CONFIG", os.path.join(BASE_DIR, "config.ini"))
    if not os.path.isfile(cfg_path):
        cfg_path = os.path.join(BASE_DIR, "config.example.ini")
    cfg.read(cfg_path, encoding="utf-8")
    return cfg


CFG = load_config()
RECORD_ROOT = CFG.get("archive", "record_root", fallback=r"E:\VMS\Record")
COPY_LIVE = CFG.getboolean("live", "copy_codec", fallback=False)
COPY_PLAYBACK = CFG.getboolean("playback", "copy_codec", fallback=False)
RTSP_TEMPLATE = CFG.get("live", "rtsp_template",
                        fallback="rtsp://{user}:{password}@{ip}:{port}/av0_0")
RTSP_PORT = CFG.getint("live", "rtsp_port", fallback=554)

DB = VmsDatabase(
    host=CFG.get("db", "host", fallback="127.0.0.1"),
    port=CFG.getint("db", "port", fallback=34176),
    user=CFG.get("db", "user", fallback="root"),
    password=CFG.get("db", "password", fallback="root"),
    db=CFG.get("db", "name", fallback="surveillancesystem"),
)

WORK_DIR = os.path.join(tempfile.gettempdir(), "vms_bridge")
LIVE = streams.LiveManager(os.path.join(WORK_DIR, "live"), RTSP_TEMPLATE,
                           copy_codec=COPY_LIVE, rtsp_port=RTSP_PORT)
PLAYBACK_DIR = os.path.join(WORK_DIR, "playback")
os.makedirs(PLAYBACK_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)

# ---- simple in-memory camera cache (refreshed every 30s) -------------------
_cam_cache: dict = {"ts": 0, "cams": []}
_cam_lock = threading.Lock()


def get_cameras(force: bool = False):
    with _cam_lock:
        if force or time.time() - _cam_cache["ts"] > 30:
            try:
                _cam_cache["cams"] = DB.list_cameras()
                _cam_cache["ts"] = time.time()
            except Exception as exc:  # keep serving the last good list
                app.logger.warning("camera list refresh failed: %s", exc)
        return _cam_cache["cams"]


def find_camera(guid: str):
    for c in get_cameras():
        if c.guid == guid:
            return c
    return None


# ---- static web app --------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(os.path.join(BASE_DIR, "static"), "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory(os.path.join(BASE_DIR, "static"), path)


# ---- API -------------------------------------------------------------------
@app.route("/api/cameras")
def api_cameras():
    cams = get_cameras(force=request.args.get("refresh") == "1")
    return jsonify([
        {"guid": c.guid, "name": c.name, "disabled": c.disabled}
        for c in cams
    ])


@app.route("/api/cameras/<guid>/days")
def api_days(guid):
    days = archive.list_days(RECORD_ROOT, guid)
    return jsonify(days)


@app.route("/api/cameras/<guid>/segments")
def api_segments(guid):
    date = request.args.get("date")
    if not date:
        abort(400, "date query parameter (YYYY-MM-DD) is required")
    segs = archive.list_segments(RECORD_ROOT, guid, date)
    return jsonify([s.to_dict() for s in segs])


# ---- live ------------------------------------------------------------------
@app.route("/live/<guid>/index.m3u8")
def live_playlist(guid):
    cam = find_camera(guid)
    if not cam:
        abort(404, "unknown camera")
    playlist = LIVE.ensure(cam)
    # wait briefly for the first segment to appear
    for _ in range(50):
        if os.path.isfile(playlist) and os.path.getsize(playlist) > 0:
            break
        time.sleep(0.1)
    if not os.path.isfile(playlist):
        abort(503, "live stream is starting, retry shortly")
    return send_file(playlist, mimetype="application/vnd.apple.mpegurl",
                     max_age=0)


@app.route("/live/<guid>/<seg>")
def live_segment(guid, seg):
    LIVE.touch(guid)
    cam_dir = os.path.join(WORK_DIR, "live", guid)
    if not os.path.isfile(os.path.join(cam_dir, seg)):
        abort(404)
    return send_from_directory(cam_dir, seg, max_age=0)


# ---- playback --------------------------------------------------------------
@app.route("/playback/<guid>/segment")
def playback_segment(guid):
    """Convert one archive segment (identified by its begin epoch) to MP4."""

    date = request.args.get("date")
    epoch = request.args.get("t", type=int)
    if not date or epoch is None:
        abort(400, "date and t (epoch) query parameters are required")

    seg = archive.find_segment_at(RECORD_ROOT, guid, date, epoch)
    if not seg:
        abort(404, "no recording at that time")
    if not os.path.isfile(seg.vdo_path):
        abort(404, "recording file missing on disk: %s" % seg.vdo_path)

    safe = seg.rel_path.replace("/", "_")
    out_path = os.path.join(PLAYBACK_DIR, f"{safe}.mp4")
    if not (os.path.isfile(out_path) and os.path.getsize(out_path) > 0):
        ok = streams.vdo_to_mp4(seg.vdo_path, out_path, copy_codec=COPY_PLAYBACK)
        if not ok:
            abort(500, "ffmpeg failed to convert the segment")
    return send_file(out_path, mimetype="video/mp4", conditional=True,
                     max_age=3600)


@app.route("/api/health")
def health():
    try:
        cams = get_cameras()
        db_ok = True
    except Exception:
        cams = []
        db_ok = False
    return jsonify({
        "db_ok": db_ok,
        "camera_count": len(cams),
        "record_root": RECORD_ROOT,
        "record_root_exists": os.path.isdir(RECORD_ROOT),
    })


if __name__ == "__main__":
    host = CFG.get("server", "host", fallback="0.0.0.0")
    port = CFG.getint("server", "port", fallback=8080)
    app.run(host=host, port=port, threaded=True)
