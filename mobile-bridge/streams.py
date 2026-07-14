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
from urllib.parse import quote

import onvif_rtsp

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


def _resolve_tool(explicit: str | None, env_var: str, default_name: str) -> str:
    if explicit:
        return explicit
    from_env = os.environ.get(env_var)
    if from_env:
        return from_env
    found = shutil.which(default_name)
    if found:
        return found
    if os.name == "nt":
        found = shutil.which(default_name + ".exe")
        if found:
            return found
    return default_name


def _tool_available(path: str) -> bool:
    return os.path.isfile(path) or shutil.which(path) is not None


def configure_tools(ffmpeg_bin: str | None = None, ffprobe_bin: str | None = None) -> None:
    """Resolve ffmpeg/ffprobe paths from config, env vars, or PATH."""

    global FFMPEG, FFPROBE
    FFMPEG = _resolve_tool(ffmpeg_bin, "FFMPEG_BIN", "ffmpeg")
    if ffprobe_bin:
        FFPROBE = ffprobe_bin
    elif os.environ.get("FFPROBE_BIN"):
        FFPROBE = os.environ["FFPROBE_BIN"]
    elif ffmpeg_bin and os.path.isfile(ffmpeg_bin):
        sibling = os.path.join(
            os.path.dirname(ffmpeg_bin),
            "ffprobe.exe" if os.name == "nt" else "ffprobe",
        )
        FFPROBE = sibling if os.path.isfile(sibling) else _resolve_tool(None, "FFPROBE_BIN", "ffprobe")
    else:
        FFPROBE = _resolve_tool(None, "FFPROBE_BIN", "ffprobe")


def tools_status() -> dict:
    return {
        "ffmpeg": FFMPEG,
        "ffprobe": FFPROBE,
        "ffmpeg_ok": _tool_available(FFMPEG),
        "ffprobe_ok": _tool_available(FFPROBE),
    }


def ensure_tools() -> None:
    """Raise FileNotFoundError with setup hints when ffmpeg/ffprobe are missing."""

    missing = [name for name, path in (("ffmpeg", FFMPEG), ("ffprobe", FFPROBE))
               if not _tool_available(path)]
    if not missing:
        return
    hint = (
        "Install ffmpeg for Windows (https://www.gyan.dev/ffmpeg/builds/), "
        "add its bin folder to PATH, or set full paths in config.ini:\n"
        "  [tools]\n"
        "  ffmpeg_bin = C:\\ffmpeg\\bin\\ffmpeg.exe\n"
        "  ffprobe_bin = C:\\ffmpeg\\bin\\ffprobe.exe"
    )
    raise FileNotFoundError(f"Missing: {', '.join(missing)}. {hint}")


def build_rtsp_url(template: str, cam, rtsp_port: int = 554) -> str:
    """Render an RTSP URL template with the camera's connection info.

    ``rtsp_port`` is the RTSP service port (default 554); it is intentionally
    separate from the device's HTTP/ONVIF port stored in the database.
    User/password are URL-encoded because special characters break RTSP URLs.
    """

    return template.format(
        user=quote(cam.user, safe=""),
        password=quote(cam.password, safe=""),
        ip=cam.ip,
        port=rtsp_port,
        http_port=cam.http_port,
        channel=cam.channel_no,
        channel0=max(0, cam.channel_no - 1),
    )


def resolve_live_url(cam, rtsp_template: str, rtsp_port: int = 554,
                     use_onvif: bool = False) -> str:
    """Pick the RTSP URL for live streaming (ONVIF discovery or template)."""

    if use_onvif:
        found = onvif_rtsp.discover_streams(cam)
        if found:
            return found[0].url
    return build_rtsp_url(rtsp_template, cam, rtsp_port)


class LiveManager:
    """Runs one ffmpeg RTSP->HLS worker per camera, on demand."""

    def __init__(self, work_dir: str, rtsp_template: str, copy_codec: bool = False,
                 idle_timeout: int = 60, rtsp_port: int = 554, use_onvif: bool = False):
        self.work_dir = work_dir
        self.rtsp_template = rtsp_template
        self.rtsp_port = rtsp_port
        self.use_onvif = use_onvif
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

            rtsp = resolve_live_url(cam, self.rtsp_template, self.rtsp_port,
                                    self.use_onvif)
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
            log_path = os.path.join(cam_dir, "ffmpeg.log")
            with open(log_path, "w", encoding="utf-8") as logf:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=logf,
                )
            self._procs[guid] = {"proc": proc, "last": time.time(), "rtsp": rtsp}
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


def probe_rtsp(url: str, timeout: int = 8, transport: str = "tcp") -> tuple[bool, str]:
    """Return (ok, error_text) from ffprobe for an RTSP url."""

    ensure_tools()
    cmd = [
        FFPROBE, "-v", "error", "-rtsp_transport", transport,
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        url,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        err = (res.stderr or res.stdout or "").strip()
        ok = res.returncode == 0 and bool((res.stdout or "").strip())
        return ok, err
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except FileNotFoundError as exc:
        raise exc
