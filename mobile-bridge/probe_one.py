"""Probe one camera IP (e.g. from its web page) for a working RTSP URL.

Usage:
    python probe_one.py 192.168.21.5
    python probe_one.py 192.168.21.5 --verbose
"""

from __future__ import annotations

import configparser
import os
import socket
import sys

import onvif_rtsp
import streams
from vms_db import Camera, VmsDatabase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv

LONGSE_PATHS = [
    "/0", "/1", "/2",
    "/11", "/12", "/1", "/2",
    "/av0_0", "/av0_1",
    "/h264_stream",
    "/cam/realmonitor?channel=1&subtype=0",
    "/cam/realmonitor?channel=1&subtype=1",
    "/onvif1", "/onvif2",
    "/live/ch00_0",
    "/user=admin_password={password}_channel=1_stream=0.sdp",
]


def load_cfg() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    path = os.path.join(BASE_DIR, "config.ini")
    if os.path.isfile(path):
        cfg.read(path, encoding="utf-8")
    else:
        cfg.read(os.path.join(BASE_DIR, "config.example.ini"), encoding="utf-8")
    return cfg


def tcp_ok(ip: str, port: int) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=2):
            return True
    except OSError:
        return False


def find_in_db(db: VmsDatabase, ip: str) -> Camera | None:
    for cam in db.list_cameras():
        if cam.ip == ip:
            return cam
    return None


def try_rtsp(label: str, url: str, password: str) -> bool:
    for transport in ("tcp", "udp"):
        ok, err = streams.probe_rtsp(url, transport=transport)
        if ok:
            print(f"[OK ] {label} ({transport})")
            print(f"      {url.replace(password, '***') if password else url}")
            return True
        if VERBOSE:
            print(f"[no ] {label} ({transport}) -> {err or 'failed'}")
        else:
            print(f"[no ] {label} ({transport})")
    return False


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print("Usage: python probe_one.py <camera-ip> [--verbose]")
        return

    ip = args[0]
    cfg = load_cfg()
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
    cam = find_in_db(db, ip)
    if cam:
        print(f"Found in VMS DB: '{cam.name}' user={cam.user} http={cam.http_port}")
    else:
        cam = Camera(
            guid="manual",
            name=ip,
            device_guid="",
            ip=ip,
            http_port=80,
            user="admin",
            password="admin",
            channel_no=1,
            disabled=False,
        )
        print(f"Not in DB — using defaults user=admin password=admin http=80")

    print(f"\nReachability from this server:")
    for port in (80, 554, 8999, 8899, cam.http_port):
        if port:
            print(f"  TCP {ip}:{port} -> {tcp_ok(ip, port)}")

    onvif_ports = []
    for p in (cam.http_port, 80, 8999, 8899):
        if p and p not in onvif_ports:
            onvif_ports.append(p)

    print("\n--- ONVIF ---")
    for port in onvif_ports:
        test = Camera(
            guid=cam.guid, name=cam.name, device_guid=cam.device_guid, ip=ip,
            http_port=port, user=cam.user, password=cam.password,
            channel_no=cam.channel_no, disabled=False,
        )
        urls = onvif_rtsp.discover_streams(test)
        if urls:
            print(f"ONVIF on port {port}:")
            for item in urls:
                if try_rtsp(f"ONVIF {item.label}", item.url, cam.password):
                    print("\n>>> config.ini:")
                    print("use_onvif = true")
                    return
        elif VERBOSE:
            print(f"[no ] ONVIF port {port}")

    print("\n--- Longse / common RTSP paths ---")
    rtsp_ports = []
    for p in (554, 80, 8999, 8899):
        if p not in rtsp_ports:
            rtsp_ports.append(p)

    from urllib.parse import quote
    user = quote(cam.user, safe="")
    password = quote(cam.password, safe="")

    for port in rtsp_ports:
        print(f"\nRTSP port {port}:")
        for path in LONGSE_PATHS:
            rendered = path.format(password=password)
            url = f"rtsp://{user}:{password}@{ip}:{port}{rendered}"
            if try_rtsp(path, url, cam.password):
                print("\n>>> config.ini under [live]:")
                if "{password}" in path:
                    print(f"rtsp_template = rtsp://{{user}}:{{password}}@{{ip}}:{{port}}{path}")
                else:
                    print(f"rtsp_template = rtsp://{{user}}:{{password}}@{{ip}}:{{port}}{path}")
                print(f"rtsp_port = {port}")
                return

    print("\nNo working URL found.")
    print("In the camera web UI (http://%s/) check:" % ip)
    print("  - Network -> RTSP port")
    print("  - ONVIF port (Longse default is often 8999)")
    print("  - user/password")


if __name__ == "__main__":
    main()
