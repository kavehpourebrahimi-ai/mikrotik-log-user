"""Find the correct RTSP URL template for your cameras.

Reads the camera list from the VMS database and tries a set of common
Longse / FreeIP RTSP URL forms against the first reachable camera, then prints
the template you should put into config.ini ([live] rtsp_template).

Usage:
    python probe_rtsp.py
"""

from __future__ import annotations

import configparser
import os

import streams
from vms_db import VmsDatabase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CANDIDATES = [
    "rtsp://{user}:{password}@{ip}:{port}/av0_0",
    "rtsp://{user}:{password}@{ip}:{port}/av0_1",
    "rtsp://{user}:{password}@{ip}:{port}/11",
    "rtsp://{user}:{password}@{ip}:{port}/12",
    "rtsp://{user}:{password}@{ip}:{port}/1",
    "rtsp://{user}:{password}@{ip}:{port}/onvif1",
    "rtsp://{user}:{password}@{ip}:{port}/live/main",
    "rtsp://{user}:{password}@{ip}:{port}/live/0/MAIN",
    "rtsp://{user}:{password}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=0",
    "rtsp://{user}:{password}@{ip}:{port}/h264/ch{channel}/main/av_stream",
    "rtsp://{user}:{password}@{ip}:{port}/Streaming/Channels/{channel}01",
]


def main() -> None:
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(BASE_DIR, "config.ini"), encoding="utf-8")
    if not cfg.sections():
        cfg.read(os.path.join(BASE_DIR, "config.example.ini"), encoding="utf-8")

    streams.configure_tools(
        ffmpeg_bin=cfg.get("tools", "ffmpeg_bin", fallback=None),
        ffprobe_bin=cfg.get("tools", "ffprobe_bin", fallback=None),
    )
    try:
        streams.ensure_tools()
    except FileNotFoundError as exc:
        print(exc)
        return

    db = VmsDatabase(
        host=cfg.get("db", "host", fallback="127.0.0.1"),
        port=cfg.getint("db", "port", fallback=34176),
        user=cfg.get("db", "user", fallback="root"),
        password=cfg.get("db", "password", fallback="root"),
        db=cfg.get("db", "name", fallback="surveillancesystem"),
    )
    cams = [c for c in db.list_cameras() if c.ip and not c.disabled]
    if not cams:
        print("No enabled cameras with an IP were found in the database.")
        return

    rtsp_port = cfg.getint("live", "rtsp_port", fallback=554)
    cam = cams[0]
    print(f"Probing against camera '{cam.name}' ({cam.ip}:{rtsp_port}) ...\n")
    for tpl in CANDIDATES:
        url = streams.build_rtsp_url(tpl, cam, rtsp_port)
        try:
            ok = streams.probe_rtsp(url)
        except FileNotFoundError as exc:
            print(exc)
            return
        print(f"[{'OK ' if ok else 'no '}] {tpl}")
        if ok:
            print("\n>>> Put this in config.ini under [live]:")
            print(f"rtsp_template = {tpl}")
            return
    print("\nNone of the common templates worked. Check the camera RTSP path "
          "in its web UI, or run ffprobe manually.")


if __name__ == "__main__":
    main()
