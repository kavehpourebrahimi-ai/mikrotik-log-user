"""VMS Mobile Bridge - a small Flask service that runs on the Windows VMS server."""

from __future__ import annotations

import configparser
import os
import tempfile
import threading
import time

from flask import (Flask, jsonify, request, send_file, send_from_directory,
                   abort, Response)

import archive
import onvif_rtsp
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
COPY_LIVE = CFG.getboolean("live", "copy_codec", fallback=True)
COPY_PLAYBACK = CFG.getboolean("playback", "copy_codec", fallback=True)
RTSP_TEMPLATE = CFG.get("live", "rtsp_template",
                        fallback="rtsp://{user}:{password}@{ip}:{port}/0")
RTSP_TEMPLATE_SUB = CFG.get("live", "rtsp_template_sub",
                            fallback="rtsp://{user}:{password}@{ip}:{port}/1")
RTSP_PORT = CFG.getint("live", "rtsp_port", fallback=554)
USE_ONVIF = CFG.getboolean("live", "use_onvif", fallback=True)
LIVE_SCALE = CFG.getint("live", "live_scale", fallback=640)
GRID_STREAM = CFG.get("live", "grid_stream", fallback="sub")

streams.configure_tools(
    ffmpeg_bin=CFG.get("tools", "ffmpeg_bin", fallback=None),
    ffprobe_bin=CFG.get("tools", "ffprobe_bin", fallback=None),
)

DB = VmsDatabase(
    host=CFG.get("db", "host", fallback="127.0.0.1"),
    port=CFG.getint("db", "port", fallback=34176),
    user=CFG.get("db", "user", fallback="root"),
    password=CFG.get("db", "password", fallback="root"),
    db=CFG.get("db", "name", fallback="surveillancesystem"),
)

WORK_DIR = os.path.join(tempfile.gettempdir(), "vms_bridge")
LIVE = streams.LiveManager(
    os.path.join(WORK_DIR, "live"), RTSP_TEMPLATE,
    copy_codec=COPY_LIVE, rtsp_port=RTSP_PORT,
    use_onvif=USE_ONVIF, live_scale=LIVE_SCALE,
    rtsp_template_sub=RTSP_TEMPLATE_SUB,
)
PLAYBACK_DIR = os.path.join(WORK_DIR, "playback")
os.makedirs(PLAYBACK_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)

_cam_cache: dict = {"ts": 0, "cams": []}
_cam_lock = threading.Lock()


def get_cameras(force: bool = False):
    with _cam_lock:
        if force or time.time() - _cam_cache["ts"] > 30:
            try:
                _cam_cache["cams"] = DB.list_cameras()
                _cam_cache["ts"] = time.time()
            except Exception as exc:
                app.logger.warning("camera list refresh failed: %s", exc)
        return _cam_cache["cams"]


def find_camera(guid: str):
    for c in get_cameras():
        if c.guid == guid:
            return c
    return None


def _norm_stream(stream: str | None) -> str:
    return "sub" if stream == "sub" else "main"


@app.route("/")
def index():
    return send_from_directory(os.path.join(BASE_DIR, "static"), "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory(os.path.join(BASE_DIR, "static"), path)


@app.route("/api/config")
def api_config():
    return jsonify({
        "grid_stream": GRID_STREAM,
        "use_onvif": USE_ONVIF,
        "copy_codec": COPY_LIVE,
    })


@app.route("/api/cameras")
def api_cameras():
    cams = get_cameras(force=request.args.get("refresh") == "1")
    return jsonify([
        {"guid": c.guid, "name": c.name, "disabled": c.disabled}
        for c in cams if not c.disabled
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


@app.route("/api/cameras/<guid>/play_at")
def api_play_at(guid):
    """Find recording at an exact date/time and return the playback URL."""

    when = request.args.get("datetime") or request.args.get("when")
    if not when:
        abort(400, "datetime=YYYY-MM-DDTHH:MM required")
    try:
        seg, date, epoch = archive.find_segment_for_datetime(RECORD_ROOT, guid, when)
    except ValueError as exc:
        abort(400, str(exc))
    if not seg:
        abort(404, "no recording at that time")
    return jsonify({
        "date": date,
        "epoch": epoch,
        "requested": when,
        "segment_begin": seg.begin,
        "segment_end": seg.end,
        "begin_iso": seg.to_dict()["begin_iso"],
        "end_iso": seg.to_dict()["end_iso"],
        "url": f"/playback/{guid}/segment?date={date}&t={seg.begin}",
        "nearest": seg.begin != epoch,
    })


@app.route("/api/cameras/<guid>/onvif")
def api_onvif(guid):
    """Test ONVIF stream discovery for one camera."""

    cam = find_camera(guid)
    if not cam:
        abort(404, "unknown camera")
    result = onvif_rtsp.discover_streams_verbose(cam)
    streams_out = [
        {"label": s.label, "url": s.url.replace(cam.password, "***") if cam.password else s.url}
        for s in result.streams
    ]
    return jsonify({
        "ok": bool(result.streams),
        "port": result.port,
        "error": result.error,
        "streams": streams_out,
    })


def _live_playlist_impl(guid: str, stream: str):
    cam = find_camera(guid)
    if not cam:
        abort(404, "unknown camera")
    stream = _norm_stream(stream)
    try:
        playlist = LIVE.ensure(cam, stream)
    except FileNotFoundError as exc:
        return Response(str(exc), status=503, mimetype="text/plain; charset=utf-8")
    # ensure() already probes / retries; wait a bit more for first .ts
    for _ in range(150):
        if os.path.isfile(playlist) and os.path.getsize(playlist) > 0:
            st = LIVE.status(guid, stream)
            if st["segment_count"] > 0:
                return send_file(playlist, mimetype="application/vnd.apple.mpegurl",
                                 max_age=0)
        if not LIVE.status(guid, stream)["proc_alive"]:
            break
        time.sleep(0.1)
    st = LIVE.status(guid, stream)
    parts = []
    if st.get("resolve_log"):
        parts.append("--- resolve ---\n" + st["resolve_log"].strip())
    if st.get("log_tail"):
        parts.append("--- ffmpeg ---\n" + st["log_tail"].strip())
    detail = "\n\n".join(parts) if parts else "ffmpeg log empty"
    if not streams.tools_status()["ffmpeg_ok"]:
        detail = "ffmpeg not found — [tools] ffmpeg_bin in config.ini"
    elif "404" in detail or "Stream Not Found" in detail:
        detail += (
            "\n\nRTSP path wrong. Open /api/live/%s/diagnose?stream=%s "
            "or run: python probe_one.py %s"
        ) % (guid, stream, cam.ip)
    elif st["proc_alive"]:
        resp = Response(
            "stream starting, retry\n\n" + detail,
            status=503, mimetype="text/plain; charset=utf-8",
        )
        resp.headers["Retry-After"] = "3"
        return resp
    detail += (
        "\n\nDiagnose: /api/live/%s/diagnose?stream=%s"
        % (guid, stream)
    )
    return Response(detail, status=503, mimetype="text/plain; charset=utf-8")


@app.route("/live/<guid>/index.m3u8")
def live_playlist_main(guid):
    return _live_playlist_impl(guid, "main")


@app.route("/live/<guid>/<stream>/index.m3u8")
def live_playlist_stream(guid, stream):
    if stream.endswith(".m3u8"):
        abort(404)
    return _live_playlist_impl(guid, stream)


@app.route("/api/live/<guid>/snapshot.jpg")
def live_snapshot(guid):
    cam = find_camera(guid)
    if not cam:
        abort(404, "unknown camera")
    stream = _norm_stream(request.args.get("stream", GRID_STREAM))
    data = LIVE.snapshot(cam, stream=stream)
    if not data:
        st = LIVE.status(guid, stream)
        abort(503, "snapshot failed: " + (st.get("log_tail") or ""))
    return Response(data, mimetype="image/jpeg", max_age=0)


@app.route("/api/live/<guid>/status")
def live_status(guid):
    cam = find_camera(guid)
    if not cam:
        abort(404, "unknown camera")
    stream = _norm_stream(request.args.get("stream", "main"))
    start = request.args.get("start", "0") in ("1", "true", "yes")
    if start:
        try:
            LIVE.ensure(cam, stream)
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 503
    st = LIVE.status(guid, stream)
    st["camera"] = cam.name
    st["ip"] = cam.ip
    if st.get("rtsp") and cam.password:
        st["rtsp"] = st["rtsp"].replace(cam.password, "***")
    return jsonify(st)


@app.route("/api/live/<guid>/diagnose")
def live_diagnose(guid):
    """Probe ONVIF + RTSP candidates without relying on a previous failed cache."""

    cam = find_camera(guid)
    if not cam:
        abort(404, "unknown camera")
    stream = _norm_stream(request.args.get("stream", "main"))
    streams.invalidate_rtsp_cache(LIVE.work_dir, cam, stream)
    return jsonify(LIVE.diagnose(cam, stream))


@app.route("/api/live/cache/clear", methods=["POST", "GET"])
def live_cache_clear():
    n = streams.invalidate_rtsp_cache(LIVE.work_dir)
    return jsonify({"ok": True, "removed": n})


@app.route("/live/<guid>/<path:rest>")
def live_segment(guid, rest):
    """Serve HLS segments for main or sub stream."""

    stream = "main"
    seg = rest
    if "/" in rest:
        stream, seg = rest.split("/", 1)
        stream = _norm_stream(stream)
    elif rest in ("main", "sub"):
        abort(404)
    LIVE.touch(guid, stream)
    cam_dir = os.path.join(WORK_DIR, "live", f"{guid}_{stream}")
    path = os.path.join(cam_dir, seg)
    if not os.path.isfile(path):
        abort(404)
    mime = "application/vnd.apple.mpegurl" if seg.endswith(".m3u8") else "video/mp2t"
    return send_from_directory(cam_dir, seg, mimetype=mime, max_age=0)


@app.route("/playback/<guid>/segment")
def playback_segment(guid):
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
    return send_file(out_path, mimetype="video/mp4", conditional=True, max_age=3600)


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
        "use_onvif": USE_ONVIF,
        **streams.tools_status(),
    })


if __name__ == "__main__":
    try:
        streams.ensure_tools()
        print("ffmpeg:", streams.FFMPEG)
        print("use_onvif:", USE_ONVIF)
        print("rtsp main:", RTSP_TEMPLATE)
        print("rtsp sub:", RTSP_TEMPLATE_SUB)
        print("record_root:", RECORD_ROOT)
    except FileNotFoundError as exc:
        print("SETUP ERROR:", exc)
        raise SystemExit(1) from exc
    host = CFG.get("server", "host", fallback="0.0.0.0")
    port = CFG.getint("server", "port", fallback=8080)
    app.run(host=host, port=port, threaded=True)
