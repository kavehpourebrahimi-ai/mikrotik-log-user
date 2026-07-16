"""ffmpeg-based live and playback stream management.

Everything is proxied through this machine (the VMS server):

* Live    - pull RTSP from the camera (credentials from the DB) and repackage
            it as HLS that any mobile browser can play.
* Playback- read the raw .vdo (Annex-B HEVC) archive segment and repackage it
            as a progressive MP4 / HLS.

HEVC is not playable in every mobile browser when repackaged as-is, so by default
the server does **not** transcode (`copy_codec=true`): it only repackages the
camera's HEVC stream into HLS/MP4 and the **client** decodes it. This keeps
server CPU low. Set ``copy_codec=false`` only if you need H.264 for old clients
and accept high CPU load on the server.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from urllib.parse import quote

import onvif_rtsp

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

# Tried in order when the configured template returns RTSP 404.
RTSP_PROBE_TEMPLATES_MAIN = [
    "rtsp://{user}:{password}@{ip}:{port}/0",
    "rtsp://{user}:{password}@{ip}:{port}/11",
    "rtsp://{user}:{password}@{ip}:{port}/12",
    "rtsp://{user}:{password}@{ip}:{port}/av0_0",
    "rtsp://{user}:{password}@{ip}:{port}/Streaming/Channels/101",
    "rtsp://{user}:{password}@{ip}:{port}/onvif1",
    "rtsp://{user}:{password}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=0",
]

RTSP_PROBE_TEMPLATES_SUB = [
    "rtsp://{user}:{password}@{ip}:{port}/1",
    "rtsp://{user}:{password}@{ip}:{port}/12",
    "rtsp://{user}:{password}@{ip}:{port}/av0_1",
    "rtsp://{user}:{password}@{ip}:{port}/Streaming/Channels/102",
    "rtsp://{user}:{password}@{ip}:{port}/onvif2",
    "rtsp://{user}:{password}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=1",
]

_rtsp_cache: dict[str, str] = {}
_cache_lock = threading.Lock()


def _cache_path(work_dir: str) -> str:
    return os.path.join(work_dir, "_rtsp_cache.json")


def load_rtsp_cache(work_dir: str) -> None:
    global _rtsp_cache
    path = _cache_path(work_dir)
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                _rtsp_cache = json.load(fh)
        except (json.JSONDecodeError, OSError):
            _rtsp_cache = {}


def save_rtsp_cache(work_dir: str) -> None:
    path = _cache_path(work_dir)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(_rtsp_cache, fh, indent=2)
    except OSError:
        pass


def invalidate_rtsp_cache(work_dir: str | None, cam=None, stream: str | None = None) -> int:
    """Drop cached RTSP URLs (optionally for one camera/stream). Returns removed count."""

    global _rtsp_cache
    removed = 0
    with _cache_lock:
        if cam is None and stream is None:
            removed = len(_rtsp_cache)
            _rtsp_cache = {}
        else:
            keys = []
            if cam is not None:
                base = cam.ip or cam.guid
                if stream:
                    keys = [f"{base}:{stream}"]
                else:
                    keys = [f"{base}:main", f"{base}:sub"]
            for k in keys:
                if k in _rtsp_cache:
                    _rtsp_cache.pop(k, None)
                    removed += 1
    if work_dir:
        save_rtsp_cache(work_dir)
    return removed


def _cache_key(cam, stream: str) -> str:
    return f"{cam.ip}:{stream}" if cam.ip else f"{cam.guid}:{stream}"


def _mask_rtsp(url: str, password: str) -> str:
    if password and password in url:
        return url.replace(password, "***")
    return url


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


def collect_rtsp_candidates(cam, rtsp_template: str, rtsp_port: int = 554,
                            use_onvif: bool = False, stream: str = "main",
                            rtsp_template_sub: str | None = None,
                            auto_probe: bool = True) -> list[dict]:
    """Build ordered RTSP candidates: cache → ONVIF (probed) → templates (probed)."""

    stream = "sub" if stream == "sub" else "main"
    tpl = rtsp_template_sub if stream == "sub" and rtsp_template_sub else rtsp_template
    key = _cache_key(cam, stream)
    candidates: list[dict] = []
    seen: set[str] = set()

    def add(url: str, source: str, template: str | None = None) -> None:
        if not url or url in seen:
            return
        seen.add(url)
        candidates.append({"url": url, "source": source, "template": template})

    with _cache_lock:
        cached = _rtsp_cache.get(key)
    if cached:
        if cached.startswith("url:"):
            add(cached[4:], "cache")
        else:
            add(build_rtsp_url(cached, cam, rtsp_port), "cache", cached)

    if use_onvif:
        found = onvif_rtsp.discover_streams(cam)
        if found:
            idx = 1 if stream == "sub" and len(found) > 1 else 0
            add(found[idx].url, f"onvif:{found[idx].label}")
            # Also keep alternate ONVIF profiles as fallbacks.
            for i, s in enumerate(found):
                if i != idx:
                    add(s.url, f"onvif:{s.label}")

    probe_list = RTSP_PROBE_TEMPLATES_SUB if stream == "sub" else RTSP_PROBE_TEMPLATES_MAIN
    templates = [tpl]
    for t in probe_list:
        if t not in templates:
            templates.append(t)
    for t in templates:
        add(build_rtsp_url(t, cam, rtsp_port), "template", t)

    if not auto_probe:
        return candidates

    ensure_tools()
    verified: list[dict] = []
    unverified: list[dict] = []
    for c in candidates:
        ok, err = probe_rtsp(c["url"], timeout=5)
        c = dict(c, probe_ok=ok, probe_err=err)
        if ok:
            verified.append(c)
        else:
            unverified.append(c)
    # Prefer probed-ok URLs; keep others as last-resort (some cameras block ffprobe).
    return verified + unverified


def resolve_live_url(cam, rtsp_template: str, rtsp_port: int = 554,
                     use_onvif: bool = False, work_dir: str | None = None,
                     auto_probe: bool = True, stream: str = "main",
                     rtsp_template_sub: str | None = None) -> str:
    """Pick a working RTSP URL (ONVIF first, cache, template, or auto-probe)."""

    candidates = collect_rtsp_candidates(
        cam, rtsp_template, rtsp_port, use_onvif, stream,
        rtsp_template_sub, auto_probe=auto_probe,
    )
    stream = "sub" if stream == "sub" else "main"
    key = _cache_key(cam, stream)
    tpl = rtsp_template_sub if stream == "sub" and rtsp_template_sub else rtsp_template

    for c in candidates:
        if c.get("probe_ok"):
            with _cache_lock:
                if c.get("template"):
                    _rtsp_cache[key] = c["template"]
                else:
                    _rtsp_cache[key] = "url:" + c["url"]
            if work_dir:
                save_rtsp_cache(work_dir)
            return c["url"]

    if candidates:
        return candidates[0]["url"]
    return build_rtsp_url(tpl, cam, rtsp_port)


class LiveManager:
    """Runs one ffmpeg RTSP->HLS worker per camera, on demand."""

    def __init__(self, work_dir: str, rtsp_template: str, copy_codec: bool = False,
                 idle_timeout: int = 60, rtsp_port: int = 554, use_onvif: bool = False,
                 live_scale: int = 640, rtsp_template_sub: str | None = None):
        self.work_dir = work_dir
        self.rtsp_template = rtsp_template
        self.rtsp_template_sub = rtsp_template_sub or "rtsp://{user}:{password}@{ip}:{port}/1"
        self.rtsp_port = rtsp_port
        self.use_onvif = use_onvif
        self.live_scale = live_scale
        self.copy_codec = copy_codec
        self.idle_timeout = idle_timeout
        self._procs: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._last_diag: dict[str, dict] = {}
        os.makedirs(work_dir, exist_ok=True)
        load_rtsp_cache(work_dir)
        threading.Thread(target=self._reaper, daemon=True).start()

    def _stream_key(self, guid: str, stream: str) -> str:
        return f"{guid}:{stream}"

    def _cam_dir(self, guid: str, stream: str = "main") -> str:
        return os.path.join(self.work_dir, f"{guid}_{stream}")

    def playlist_path(self, guid: str, stream: str = "main") -> str:
        return os.path.join(self._cam_dir(guid, stream), "live.m3u8")

    def diagnose(self, cam, stream: str = "main") -> dict:
        """Probe all RTSP candidates without starting ffmpeg (for UI/API)."""

        stream = "sub" if stream == "sub" else "main"
        try:
            ensure_tools()
        except FileNotFoundError as exc:
            return {"ok": False, "error": str(exc), "candidates": []}

        onvif_info = onvif_rtsp.discover_streams_verbose(cam) if self.use_onvif else None
        candidates = collect_rtsp_candidates(
            cam, self.rtsp_template, self.rtsp_port, self.use_onvif, stream,
            self.rtsp_template_sub, auto_probe=True,
        )
        out = []
        for c in candidates:
            out.append({
                "source": c["source"],
                "url": _mask_rtsp(c["url"], cam.password),
                "probe_ok": bool(c.get("probe_ok")),
                "probe_err": (c.get("probe_err") or "")[:300],
            })
        ok_any = any(x["probe_ok"] for x in out)
        result = {
            "ok": ok_any,
            "camera": cam.name,
            "ip": cam.ip,
            "http_port": cam.http_port,
            "stream": stream,
            "use_onvif": self.use_onvif,
            "onvif_port": onvif_info.port if onvif_info else None,
            "onvif_error": onvif_info.error if onvif_info and not onvif_info.streams else "",
            "onvif_streams": len(onvif_info.streams) if onvif_info else 0,
            "candidates": out,
            "tools": tools_status(),
        }
        self._last_diag[self._stream_key(cam.guid, stream)] = result
        return result

    def _write_resolve_log(self, cam_dir: str, attempts: list[dict], cam) -> None:
        path = os.path.join(cam_dir, "resolve.log")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                for a in attempts:
                    fh.write(
                        f"{a.get('source')} probe={a.get('probe_ok')} "
                        f"ffmpeg_alive={a.get('ffmpeg_alive')} "
                        f"url={_mask_rtsp(a.get('url', ''), cam.password)}\n"
                        f"  err={a.get('err', '')[:400]}\n"
                    )
        except OSError:
            pass

    def _start_ffmpeg(self, cam, cam_dir: str, rtsp: str, stream: str,
                      transport: str = "tcp") -> subprocess.Popen:
        vf = []
        if not self.copy_codec and self.live_scale > 0:
            vf = ["-vf", f"scale={self.live_scale}:-2"]
        vcodec = ["-c:v", "copy"] if self.copy_codec else [
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
            "-pix_fmt", "yuv420p", "-g", "25", "-keyint_min", "25", "-threads", "2",
        ]
        # Live RTSP is usually already Annex-B; do NOT apply hevc_mp4toannexb here
        # (that filter is for MP4 length-prefixed HEVC and can kill live ffmpeg).
        cmd = [
            FFMPEG, "-nostdin", "-loglevel", "info",
            "-rtsp_transport", transport,
            "-fflags", "nobuffer+genpts", "-flags", "low_delay",
            "-probesize", "1000000", "-analyzeduration", "2000000",
            "-i", rtsp,
            "-an", *vf, *vcodec,
            "-f", "hls",
            "-hls_time", "2",
            "-hls_list_size", "6",
            "-hls_flags", "delete_segments+append_list+omit_endlist+independent_segments",
            "-hls_segment_filename", os.path.join(cam_dir, "seg%d.ts"),
            self.playlist_path(cam.guid, stream),
        ]
        log_path = os.path.join(cam_dir, "ffmpeg.log")
        shown_rtsp = _mask_rtsp(rtsp, cam.password)
        with open(log_path, "w", encoding="utf-8") as logf:
            logf.write(f"stream: {stream}\n")
            logf.write(f"transport: {transport}\n")
            logf.write("ffmpeg: " + FFMPEG + "\n")
            logf.write("copy_codec: " + str(self.copy_codec) + "\n")
            logf.write("rtsp: " + shown_rtsp + "\n")
            logf.write("cmd: " + " ".join(cmd[:8]) + " ...\n\n")
            logf.flush()
            return subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=logf,
            )

    def ensure(self, cam, stream: str = "main") -> str:
        """Start (or reuse) a live HLS worker; return the playlist file path."""

        stream = "sub" if stream == "sub" else "main"
        guid = cam.guid
        proc_key = self._stream_key(guid, stream)

        with self._lock:
            info = self._procs.get(proc_key)
            if info and info["proc"].poll() is None:
                info["last"] = time.time()
                return self.playlist_path(guid, stream)
            if info:
                self._procs.pop(proc_key, None)

        ensure_tools()
        cam_dir = self._cam_dir(guid, stream)
        os.makedirs(cam_dir, exist_ok=True)
        for f in os.listdir(cam_dir):
            try:
                os.remove(os.path.join(cam_dir, f))
            except OSError:
                pass

        # Probe ONVIF + templates; verified URLs first, then unverified fallbacks.
        candidates = collect_rtsp_candidates(
            cam, self.rtsp_template, self.rtsp_port, self.use_onvif, stream,
            self.rtsp_template_sub, auto_probe=True,
        )
        if not candidates:
            tpl = self.rtsp_template_sub if stream == "sub" else self.rtsp_template
            candidates = [{
                "url": build_rtsp_url(tpl, cam, self.rtsp_port),
                "source": "fallback",
                "probe_ok": None,
            }]

        attempts: list[dict] = []
        last_proc = None
        last_rtsp = ""

        # Try up to 4 distinct URLs; for first URL also try UDP if TCP dies.
        tried = 0
        for c in candidates:
            if tried >= 4:
                break
            tried += 1
            for transport in ("tcp", "udp"):
                # Clean previous attempt files (keep resolve.log written at end).
                for f in os.listdir(cam_dir):
                    if f.endswith(".ts") or f.endswith(".m3u8") or f == "ffmpeg.log":
                        try:
                            os.remove(os.path.join(cam_dir, f))
                        except OSError:
                            pass
                try:
                    proc = self._start_ffmpeg(cam, cam_dir, c["url"], stream, transport)
                except FileNotFoundError:
                    raise

                # Wait briefly: if ffmpeg dies immediately, try next URL/transport.
                time.sleep(2.5)
                alive = proc.poll() is None
                playlist = self.playlist_path(guid, stream)
                has_pl = os.path.isfile(playlist) and os.path.getsize(playlist) > 0
                log_tail = ""
                log_path = os.path.join(cam_dir, "ffmpeg.log")
                if os.path.isfile(log_path):
                    with open(log_path, encoding="utf-8", errors="replace") as fh:
                        log_tail = fh.read()[-800:]

                attempts.append({
                    "source": c.get("source"),
                    "url": c["url"],
                    "transport": transport,
                    "probe_ok": c.get("probe_ok"),
                    "ffmpeg_alive": alive,
                    "playlist": has_pl,
                    "err": "" if alive else log_tail,
                })

                if alive or has_pl:
                    last_proc = proc
                    last_rtsp = c["url"]
                    # Cache working choice.
                    key = _cache_key(cam, stream)
                    with _cache_lock:
                        if c.get("template"):
                            _rtsp_cache[key] = c["template"]
                        else:
                            _rtsp_cache[key] = "url:" + c["url"]
                    save_rtsp_cache(self.work_dir)
                    with self._lock:
                        self._procs[proc_key] = {
                            "proc": proc, "last": time.time(), "rtsp": c["url"],
                            "stream": stream, "guid": guid, "transport": transport,
                        }
                    self._write_resolve_log(cam_dir, attempts, cam)
                    return playlist

                try:
                    proc.kill()
                except OSError:
                    pass
                # UDP only as secondary for same URL; then move to next candidate.
                if transport == "tcp" and ("404" in log_tail or "Not Found" in log_tail
                                          or "401" in log_tail or "403" in log_tail):
                    break  # path/auth wrong — UDP won't help

        self._write_resolve_log(cam_dir, attempts, cam)
        # Keep last failed process out of registry; status reads log from disk.
        if last_proc is None and attempts:
            # Start one more time with best candidate so status has a fresh log.
            best = next((a for a in attempts if a.get("probe_ok")), attempts[0])
            try:
                proc = self._start_ffmpeg(cam, cam_dir, best["url"], stream, "tcp")
                last_proc = proc
                last_rtsp = best["url"]
                with self._lock:
                    self._procs[proc_key] = {
                        "proc": proc, "last": time.time(), "rtsp": best["url"],
                        "stream": stream, "guid": guid, "transport": "tcp",
                    }
            except FileNotFoundError:
                raise
        elif last_proc is not None:
            with self._lock:
                self._procs[proc_key] = {
                    "proc": last_proc, "last": time.time(), "rtsp": last_rtsp,
                    "stream": stream, "guid": guid,
                }

        return self.playlist_path(guid, stream)

    def touch(self, guid: str, stream: str = "main") -> None:
        proc_key = self._stream_key(guid, stream)
        with self._lock:
            if proc_key in self._procs:
                self._procs[proc_key]["last"] = time.time()

    def stop(self, guid: str, stream: str = "main") -> None:
        proc_key = self._stream_key(guid, stream)
        with self._lock:
            info = self._procs.pop(proc_key, None)
        if info:
            try:
                info["proc"].terminate()
            except OSError:
                pass

    def status(self, guid: str, stream: str = "main") -> dict:
        cam_dir = self._cam_dir(guid, stream)
        playlist = self.playlist_path(guid, stream)
        log_path = os.path.join(cam_dir, "ffmpeg.log")
        resolve_path = os.path.join(cam_dir, "resolve.log")
        proc_key = self._stream_key(guid, stream)
        with self._lock:
            info = self._procs.get(proc_key)
        proc_alive = bool(info and info["proc"].poll() is None)
        segments = []
        if os.path.isdir(cam_dir):
            segments = sorted(
                f for f in os.listdir(cam_dir)
                if f.startswith("seg") and f.endswith(".ts")
            )
        log_tail = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as fh:
                log_tail = fh.read()[-2000:]
        resolve_log = ""
        if os.path.isfile(resolve_path):
            with open(resolve_path, encoding="utf-8", errors="replace") as fh:
                resolve_log = fh.read()[-2000:]
        return {
            "proc_alive": proc_alive,
            "ffmpeg": FFMPEG,
            "playlist_exists": os.path.isfile(playlist),
            "playlist_bytes": os.path.getsize(playlist) if os.path.isfile(playlist) else 0,
            "segment_count": len(segments),
            "segments": segments[-4:],
            "rtsp": info.get("rtsp", "") if info else "",
            "transport": info.get("transport", "") if info else "",
            "stream": stream,
            "log_tail": log_tail,
            "resolve_log": resolve_log,
        }

    def snapshot(self, cam, stream: str = "sub", timeout: int = 15) -> bytes | None:
        """Grab a single JPEG frame from the camera RTSP stream."""

        ensure_tools()
        rtsp = resolve_live_url(
            cam, self.rtsp_template, self.rtsp_port, self.use_onvif,
            work_dir=self.work_dir, stream=stream,
            rtsp_template_sub=self.rtsp_template_sub,
        )
        cmd = [
            FFMPEG, "-nostdin", "-loglevel", "error",
            "-rtsp_transport", "tcp",
            "-i", rtsp,
            "-an", "-frames:v", "1",
            "-f", "image2", "-q:v", "4",
            "pipe:1",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
        if res.returncode != 0 or not res.stdout:
            return None
        return res.stdout

    def _reaper(self) -> None:
        while True:
            time.sleep(10)
            now = time.time()
            with self._lock:
                for proc_key, info in list(self._procs.items()):
                    dead = info["proc"].poll() is not None
                    idle = now - info["last"] > self.idle_timeout
                    if dead or idle:
                        try:
                            info["proc"].terminate()
                        except OSError:
                            pass
                        self._procs.pop(proc_key, None)


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
        "-bsf:v", "hevc_mp4toannexb",
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
