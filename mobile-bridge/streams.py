"""ffmpeg-based live and playback stream management.

Everything is proxied through this machine (the VMS server):

* Live    - pull RTSP from the camera (credentials from the DB) and repackage
            it as HLS that any mobile browser can play.
* Playback- read the raw .vdo (Annex-B HEVC) archive segment and repackage it
            as a progressive MP4 / HLS.

HEVC is not playable in most mobile browsers, so by default the video is
transcoded to H.264. Set ``copy_codec=True`` to avoid transcoding when you know
the client can decode HEVC (lower CPU, but limited browser support).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time

FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")


def build_rtsp_url(template: str, cam) -> str:
    """Render an RTSP URL template with the camera's connection info."""

    return template.format(
        user=cam.user,
        password=cam.password,
        ip=cam.ip,
        port=cam.port or 554,
        channel=cam.channel_no,
        channel0=max(0, cam.channel_no - 1),
    )


class LiveManager:
    """Runs one ffmpeg RTSP->HLS worker per camera, on demand."""

    def __init__(self, work_dir: str, rtsp_template: str, copy_codec: bool = False,
                 idle_timeout: int = 60):
        self.work_dir = work_dir
        self.rtsp_template = rtsp_template
        self.copy_codec = copy_codec
        self.idle_timeout = idle_timeout
        self._procs: dict[str, dict] = {}
        self._lock = threading.Lock()
        os.makedirs(work_dir, exist_ok=True)
        threading.Thread(target=self._reaper, daemon=True).start()

    def _cam_dir(self, guid: str) -> str:
        return os.path.join(self.work_dir, guid)

    def playlist_path(self, guid: str) -> str:
        return os.path.join(self._cam_dir(guid), "live.m3u8")

    def ensure(self, cam) -> str:
        """Start (or reuse) a live HLS worker; return the playlist file path."""

        guid = cam.guid
        with self._lock:
            info = self._procs.get(guid)
            if info and info["proc"].poll() is None:
                info["last"] = time.time()
                return self.playlist_path(guid)

            cam_dir = self._cam_dir(guid)
            os.makedirs(cam_dir, exist_ok=True)
            for f in os.listdir(cam_dir):
                try:
                    os.remove(os.path.join(cam_dir, f))
                except OSError:
                    pass

            rtsp = build_rtsp_url(self.rtsp_template, cam)
            vcodec = ["-c:v", "copy"] if self.copy_codec else [
                "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
                "-pix_fmt", "yuv420p", "-g", "50",
            ]
            cmd = [
                FFMPEG, "-nostdin", "-loglevel", "warning",
                "-rtsp_transport", "tcp",
                "-i", rtsp,
                "-an", *vcodec,
                "-f", "hls",
                "-hls_time", "1",
                "-hls_list_size", "4",
                "-hls_flags", "delete_segments+append_list+omit_endlist",
                "-hls_segment_filename", os.path.join(cam_dir, "seg%d.ts"),
                self.playlist_path(guid),
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            self._procs[guid] = {"proc": proc, "last": time.time()}
            return self.playlist_path(guid)

    def touch(self, guid: str) -> None:
        with self._lock:
            if guid in self._procs:
                self._procs[guid]["last"] = time.time()

    def _reaper(self) -> None:
        while True:
            time.sleep(10)
            now = time.time()
            with self._lock:
                for guid, info in list(self._procs.items()):
                    dead = info["proc"].poll() is not None
                    idle = now - info["last"] > self.idle_timeout
                    if dead or idle:
                        try:
                            info["proc"].terminate()
                        except OSError:
                            pass
                        self._procs.pop(guid, None)


def vdo_to_mp4(vdo_path: str, out_path: str, copy_codec: bool = False,
               fps: int = 25) -> bool:
    """Remux/transcode one raw HEVC .vdo segment into a playable MP4."""

    if not os.path.isfile(vdo_path):
        return False
    vcodec = ["-c:v", "copy"] if copy_codec else [
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
    ]
    cmd = [
        FFMPEG, "-nostdin", "-loglevel", "error", "-y",
        "-r", str(fps), "-f", "hevc", "-i", vdo_path,
        "-an", *vcodec, "-movflags", "+faststart",
        out_path,
    ]
    res = subprocess.run(cmd)
    return res.returncode == 0 and os.path.isfile(out_path)


def probe_rtsp(url: str, timeout: int = 8) -> bool:
    """Return True if ffprobe can open the RTSP url and find a video stream."""

    cmd = [
        "ffprobe", "-v", "error", "-rtsp_transport", "tcp",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        url,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return res.returncode == 0 and bool(res.stdout.strip())
    except subprocess.TimeoutExpired:
        return False
