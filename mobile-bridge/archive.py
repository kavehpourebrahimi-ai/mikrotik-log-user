"""Read the VMS on-disk recording archive (.map / .idx / .vdo).

The recording layout produced by the Windows VMS StreamServer is:

    <RecordRoot>/<CameraGUID>/<YYYY-MM-DD>/<CameraGUID>.map        (daily index)
    <RecordRoot>/<CameraGUID>/<YYYY-MM-DD>/<HH-MM-SS>/<CameraGUID>_<N>.vdo
    <RecordRoot>/<CameraGUID>/<YYYY-MM-DD>/<HH-MM-SS>/<CameraGUID>_<N>.idx

The `.map` file is a per-camera, per-day table of every recorded segment.
Its format (reverse engineered) is:

    offset 0x00  uint32   version (== 1)
    offset 0x04  uint32   entry_count
    offset 0x08  first entry; each entry is 88 bytes:
        +0x00 uint32  flag1
        +0x04 uint32  flag2
        +0x08 uint32  begin_time  (unix epoch, UTC)
        +0x0c uint32  end_time    (unix epoch, UTC)
        +0x10 char[72] path  ("<GUID>/<YYYY-MM-DD>/<HH-MM-SS>/<N>", NUL padded)

The `.vdo` file is a raw Annex-B HEVC (H.265) elementary stream, so it can be
remuxed to MP4 with a plain `ffmpeg -f hevc -i file.vdo -c copy out.mp4`.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

MAP_HEADER_SIZE = 0x08
MAP_ENTRY_SIZE = 88
MAP_PATH_OFFSET = 0x10
MAP_PATH_MAX = MAP_ENTRY_SIZE - MAP_PATH_OFFSET


@dataclass
class Segment:
    """One continuous recorded segment (== one .vdo file)."""

    camera_guid: str
    begin: int          # unix epoch seconds (UTC)
    end: int            # unix epoch seconds (UTC)
    rel_path: str       # "<GUID>/<date>/<HH-MM-SS>/<N>" as stored in the .map
    vdo_path: str       # absolute path to the .vdo file on disk

    @property
    def duration(self) -> int:
        return max(0, self.end - self.begin)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["duration"] = self.duration
        d["begin_iso"] = datetime.fromtimestamp(self.begin, timezone.utc).isoformat()
        d["end_iso"] = datetime.fromtimestamp(self.end, timezone.utc).isoformat()
        return d


def _u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def parse_map(map_path: str, record_root: str) -> list[Segment]:
    """Parse a single .map file into a list of :class:`Segment`."""

    with open(map_path, "rb") as fh:
        buf = fh.read()

    if len(buf) < MAP_HEADER_SIZE:
        return []

    count = _u32(buf, 0x04)
    segments: list[Segment] = []

    for i in range(count):
        base = MAP_HEADER_SIZE + i * MAP_ENTRY_SIZE
        if base + MAP_ENTRY_SIZE > len(buf):
            break
        begin = _u32(buf, base + 0x08)
        end = _u32(buf, base + 0x0C)
        raw_path = buf[base + MAP_PATH_OFFSET: base + MAP_ENTRY_SIZE]
        nul = raw_path.find(b"\x00")
        if nul != -1:
            raw_path = raw_path[:nul]
        try:
            rel = raw_path.decode("latin1")
        except Exception:
            continue
        if not rel:
            continue

        # rel = "<GUID>/<YYYY-MM-DD>/<HH-MM-SS>/<N>"
        parts = rel.split("/")
        if len(parts) < 4:
            continue
        guid, date, hms, index = parts[0], parts[1], parts[2], parts[3]
        vdo_path = os.path.join(
            record_root, guid, date, hms, f"{guid}_{index}.vdo"
        )
        segments.append(
            Segment(
                camera_guid=guid,
                begin=begin,
                end=end,
                rel_path=rel,
                vdo_path=vdo_path,
            )
        )

    segments.sort(key=lambda s: s.begin)
    return segments


def list_days(record_root: str, camera_guid: str) -> list[str]:
    """Return the list of dates (YYYY-MM-DD) that have recordings for a camera."""

    cam_dir = os.path.join(record_root, camera_guid)
    if not os.path.isdir(cam_dir):
        return []
    days = []
    for name in os.listdir(cam_dir):
        full = os.path.join(cam_dir, name)
        if os.path.isdir(full) and len(name) == 10 and name[4] == "-":
            days.append(name)
    days.sort()
    return days


def list_segments(record_root: str, camera_guid: str, date: str) -> list[Segment]:
    """Return all recorded segments for a camera on a given date."""

    map_path = os.path.join(record_root, camera_guid, date, f"{camera_guid}.map")
    if not os.path.isfile(map_path):
        return []
    return parse_map(map_path, record_root)


def find_segment_at(record_root: str, camera_guid: str, date: str, epoch: int):
    """Find the segment covering a given epoch time (or the next one after it)."""

    segs = list_segments(record_root, camera_guid, date)
    for s in segs:
        if s.begin <= epoch <= s.end:
            return s
    # fall back to the first segment that starts after the requested time
    for s in segs:
        if s.begin >= epoch:
            return s
    return None
