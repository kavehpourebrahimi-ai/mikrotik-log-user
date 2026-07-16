"""Quick pre-flight check before running probe_rtsp.py or app.py.

Usage:
    python check_setup.py
"""

from __future__ import annotations

import configparser
import os
import subprocess
import sys

import streams
from vms_db import VmsDatabase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_cfg() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    path = os.path.join(BASE_DIR, "config.ini")
    if os.path.isfile(path):
        cfg.read(path, encoding="utf-8")
    else:
        print("WARN: config.ini not found — using config.example.ini")
        cfg.read(os.path.join(BASE_DIR, "config.example.ini"), encoding="utf-8")
    return cfg


def check_tool(label: str, path: str) -> bool:
    try:
        res = subprocess.run(
            [path, "-version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        print(f"[FAIL] {label}: not found ({path})")
        return False
    except subprocess.TimeoutExpired:
        print(f"[FAIL] {label}: timed out")
        return False
    if res.returncode != 0:
        print(f"[FAIL] {label}: exited with code {res.returncode}")
        return False
    first = (res.stdout or res.stderr or "").splitlines()[0]
    print(f"[ OK ] {label}: {first}")
    return True


def main() -> int:
    print("VMS Mobile Bridge — setup check\n")
    cfg = load_cfg()
    streams.configure_tools(
        ffmpeg_bin=cfg.get("tools", "ffmpeg_bin", fallback=None),
        ffprobe_bin=cfg.get("tools", "ffprobe_bin", fallback=None),
    )
    status = streams.tools_status()
    print(f"ffmpeg path : {status['ffmpeg']}")
    print(f"ffprobe path: {status['ffprobe']}\n")

    ok_ffmpeg = check_tool("ffmpeg", status["ffmpeg"])
    ok_ffprobe = check_tool("ffprobe", status["ffprobe"])
    if not (ok_ffmpeg and ok_ffprobe):
        print("\nFix: install ffmpeg and add to config.ini:")
        print("  [tools]")
        print("  ffmpeg_bin = C:\\ffmpeg\\bin\\ffmpeg.exe")
        print("  ffprobe_bin = C:\\ffmpeg\\bin\\ffprobe.exe")
        return 1

    try:
        db = VmsDatabase(
            host=cfg.get("db", "host", fallback="127.0.0.1"),
            port=cfg.getint("db", "port", fallback=34176),
            user=cfg.get("db", "user", fallback="root"),
            password=cfg.get("db", "password", fallback="root"),
            db=cfg.get("db", "name", fallback="surveillancesystem"),
        )
        cams = db.list_cameras()
        enabled = [c for c in cams if c.ip and not c.disabled]
        print(f"\n[ OK ] database: {len(cams)} cameras ({len(enabled)} enabled with IP)")
        if enabled:
            c = enabled[0]
            print(f"       sample: {c.name} @ {c.ip}")
    except Exception as exc:
        print(f"\n[FAIL] database: {exc}")
        return 1

    record_root = cfg.get("archive", "record_root", fallback=r"E:\VMS\Record")
    if os.path.isdir(record_root):
        print(f"[ OK ] archive: {record_root}")
    else:
        print(f"[WARN] archive path not found: {record_root}")

    try:
        import onvif  # noqa: F401
        print("[ OK ] onvif-zeep installed")
    except ImportError:
        print("[FAIL] onvif-zeep — run: pip install onvif-zeep")
        return 1

    use_onvif = cfg.getboolean("live", "use_onvif", fallback=True)
    if use_onvif and enabled:
        c = enabled[0]
        import onvif_rtsp
        r = onvif_rtsp.discover_streams_verbose(c)
        if r.streams:
            print(f"[ OK ] ONVIF: {len(r.streams)} stream(s) on port {r.port} for {c.ip}")
        else:
            print(f"[WARN] ONVIF failed for sample camera: {r.error}")

    print("\nAll good — run: start.bat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
