"""Test live HLS for one camera by GUID or IP.

Usage:
    python test_live.py 192.168.21.5
    python test_live.py --guid <channel-guid>
"""

from __future__ import annotations

import configparser
import os
import sys
import time
import urllib.request

import streams
from vms_db import VmsDatabase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(BASE_DIR, "config.ini"), encoding="utf-8")
    streams.configure_tools(
        ffmpeg_bin=cfg.get("tools", "ffmpeg_bin", fallback=None),
        ffprobe_bin=cfg.get("tools", "ffprobe_bin", fallback=None),
    )
    streams.ensure_tools()

    db = VmsDatabase(
        host=cfg.get("db", "host", fallback="127.0.0.1"),
        port=cfg.getint("db", "port", fallback=34176),
        user=cfg.get("db", "user", fallback="root"),
        password=cfg.get("db", "password", fallback="root"),
        db=cfg.get("db", "name", fallback="surveillancesystem"),
    )
    cams = db.list_cameras()
    cam = None
    if "--guid" in sys.argv:
        i = sys.argv.index("--guid")
        guid = sys.argv[i + 1]
        cam = next((c for c in cams if c.guid == guid), None)
    elif len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        ip = sys.argv[1]
        cam = next((c for c in cams if c.ip == ip), None)

    if not cam:
        print("Camera not found in database.")
        return 1

    template = cfg.get("live", "rtsp_template",
                        fallback="rtsp://{user}:{password}@{ip}:{port}/0")
    rtsp_port = cfg.getint("live", "rtsp_port", fallback=554)
    rtsp = streams.build_rtsp_url(template, cam, rtsp_port)
    print(f"Camera: {cam.name}")
    print(f"RTSP:   {rtsp.replace(cam.password, '***')}")

    ok, err = streams.probe_rtsp(rtsp)
    print(f"ffprobe: {'OK' if ok else 'FAIL'}")
    if not ok:
        print(err)
        return 1

    port = cfg.getint("server", "port", fallback=8080)
    url = f"http://127.0.0.1:{port}/live/{cam.guid}/index.m3u8"
    print(f"\nRequesting HLS: {url}")
    print("(app.py must be running in another window)\n")

    for i in range(60):
        try:
            with urllib.request.urlopen(url, timeout=45) as resp:
                body = resp.read(500).decode("utf-8", errors="replace")
            print(f"[{i+1}] OK — playlist preview:\n{body[:200]}")
            return 0
        except Exception as exc:
            print(f"[{i+1}] waiting... {exc}")
            time.sleep(2)

    print("Timed out. Check %TEMP%\\vms_bridge\\live\\<guid>\\ffmpeg.log")
    return 1


if __name__ == "__main__":
    sys.exit(main())
