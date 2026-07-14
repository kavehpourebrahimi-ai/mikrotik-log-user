"""Find the correct RTSP URL template for your cameras.

Reads the camera list from the VMS database, tries ONVIF GetStreamUri first,
then common RTSP URL forms, and prints the template for config.ini.

Usage:
    python probe_rtsp.py
    python probe_rtsp.py --verbose
"""

from __future__ import annotations

import configparser
import os
import socket
import sys

import onvif_rtsp
import streams
from vms_db import VmsDatabase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv

CANDIDATES = [
    "rtsp://{user}:{password}@{ip}:{port}/0",
    "rtsp://{user}:{password}@{ip}:{port}/1",
    "rtsp://{user}:{password}@{ip}:{port}/2",
    "rtsp://{user}:{password}@{ip}:{port}/av0_0",
    "rtsp://{user}:{password}@{ip}:{port}/av0_1",
    "rtsp://{user}:{password}@{ip}:{port}/11",
    "rtsp://{user}:{password}@{ip}:{port}/12",
    "rtsp://{user}:{password}@{ip}:{port}/1",
    "rtsp://{user}:{password}@{ip}:{port}/2",
    "rtsp://{user}:{password}@{ip}:{port}/onvif1",
    "rtsp://{user}:{password}@{ip}:{port}/onvif2",
    "rtsp://{user}:{password}@{ip}:{port}/live/main",
    "rtsp://{user}:{password}@{ip}:{port}/live/0/MAIN",
    "rtsp://{user}:{password}@{ip}:{port}/live/0/SUB",
    "rtsp://{user}:{password}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=0",
    "rtsp://{user}:{password}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=1",
    "rtsp://{user}:{password}@{ip}:{port}/h264/ch{channel}/main/av_stream",
    "rtsp://{user}:{password}@{ip}:{port}/h264/ch{channel}/sub/av_stream",
    "rtsp://{user}:{password}@{ip}:{port}/Streaming/Channels/{channel}01",
    "rtsp://{user}:{password}@{ip}:{port}/Streaming/Channels/{channel}02",
    "rtsp://{user}:{password}@{ip}:{port}/stream1",
    "rtsp://{user}:{password}@{ip}:{port}/stream2",
    "rtsp://{user}:{password}@{ip}:{port}/media/video1",
    "rtsp://{user}:{password}@{ip}:{port}/media/video2",
    "rtsp://{user}:{password}@{ip}:{port}/ucast/11",
    "rtsp://{user}:{password}@{ip}:{port}/ucast/12",
]


def mask_url(url: str, password: str) -> str:
    if password:
        return url.replace(password, "***")
    return url


def tcp_reachable(ip: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def try_url(label: str, url: str, password: str) -> str | None:
    for transport in ("tcp", "udp"):
        ok, err = streams.probe_rtsp(url, transport=transport)
        if ok:
            print(f"[OK ] {label} ({transport})")
            if VERBOSE:
                print(f"      {mask_url(url, password)}")
            return url
        print(f"[no ] {label} ({transport})")
        if VERBOSE and err:
            print(f"      {err}")
    return None


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
    print(f"Probing camera '{cam.name}'")
    print(f"  IP={cam.ip}  user={cam.user}  http/onvif={cam.http_port}  rtsp={rtsp_port}")
    print(f"  TCP 554 reachable: {tcp_reachable(cam.ip, 554)}")
    print(f"  ONVIF port reachable: {tcp_reachable(cam.ip, cam.http_port)}\n")

    print("--- ONVIF GetStreamUri ---")
    onvif_urls = onvif_rtsp.discover_streams(cam)
    if not onvif_urls:
        print("[no ] ONVIF returned no RTSP URLs (install: pip install onvif-zeep)")
    for item in onvif_urls:
        hit = try_url(f"ONVIF {item.label}", item.url, cam.password)
        if hit:
            print("\n>>> ONVIF URL works. Put this in config.ini under [live]:")
            print("use_onvif = true")
            print(f"\nWorking URL example:\n{mask_url(hit, cam.password)}")
            return

    print("\n--- common RTSP templates ---")
    ports = [rtsp_port]
    if cam.http_port not in ports:
        ports.append(cam.http_port)
    for port in ports:
        if port != rtsp_port:
            print(f"\n(also trying rtsp port {port})")
        for tpl in CANDIDATES:
            url = streams.build_rtsp_url(tpl, cam, port)
            hit = try_url(tpl.replace("{port}", str(port)), url, cam.password)
            if hit:
                print("\n>>> Put this in config.ini under [live]:")
                print(f"rtsp_template = {tpl}")
                if port != rtsp_port:
                    print(f"rtsp_port = {port}")
                return

    print("\nNone of the URLs worked.")
    print("Next checks:")
    print("  1) Open the camera web UI and find the RTSP path")
    print("  2) Run with verbose errors: python probe_rtsp.py --verbose")
    print("  3) Test manually:")
    print(f"     ffprobe -rtsp_transport tcp -i \"rtsp://{cam.user}:***@{cam.ip}:554/...\"")


if __name__ == "__main__":
    main()
