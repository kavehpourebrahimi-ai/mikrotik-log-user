"""Export camera credentials from the VMS MySQL database.

Usage:
    python export_cameras.py
    python export_cameras.py --ip 192.168.21.5
    python export_cameras.py --csv cameras.csv
"""

from __future__ import annotations

import argparse
import configparser
import csv
import os
import sys

from vms_db import VmsDatabase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_cfg() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    path = os.path.join(BASE_DIR, "config.ini")
    if os.path.isfile(path):
        cfg.read(path, encoding="utf-8")
    else:
        cfg.read(os.path.join(BASE_DIR, "config.example.ini"), encoding="utf-8")
    return cfg


def main() -> int:
    parser = argparse.ArgumentParser(description="Export VMS camera credentials")
    parser.add_argument("--ip", help="filter by camera IP")
    parser.add_argument("--csv", metavar="FILE", help="write CSV to this file")
    parser.add_argument("--show-disabled", action="store_true",
                        help="include disabled cameras")
    args = parser.parse_args()

    cfg = load_cfg()
    db = VmsDatabase(
        host=cfg.get("db", "host", fallback="127.0.0.1"),
        port=cfg.getint("db", "port", fallback=34176),
        user=cfg.get("db", "user", fallback="root"),
        password=cfg.get("db", "password", fallback="root"),
        db=cfg.get("db", "name", fallback="surveillancesystem"),
    )

    try:
        cams = db.list_cameras()
    except Exception as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1

    if args.ip:
        cams = [c for c in cams if c.ip == args.ip]
    if not args.show_disabled:
        cams = [c for c in cams if not c.disabled]

    rows = [{
        "name": c.name,
        "ip": c.ip,
        "http_port": c.http_port,
        "user": c.user,
        "password": c.password,
        "channel": c.channel_no,
        "guid": c.guid,
        "disabled": c.disabled,
    } for c in cams]

    if not rows:
        print("No cameras matched.")
        return 1

    fields = ["name", "ip", "http_port", "user", "password", "channel", "guid", "disabled"]

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} cameras to {args.csv}")
        return 0

    widths = {f: max(len(f), *(len(str(r[f])) for r in rows)) for f in fields}
    header = "  ".join(f.ljust(widths[f]) for f in fields)
    print(header)
    print("-" * len(header))
    for row in rows:
        print("  ".join(str(row[f]).ljust(widths[f]) for f in fields))
    print(f"\nTotal: {len(rows)} cameras")
    return 0


if __name__ == "__main__":
    sys.exit(main())
