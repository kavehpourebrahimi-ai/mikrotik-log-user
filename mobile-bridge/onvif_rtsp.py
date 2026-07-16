"""Discover camera RTSP URLs through ONVIF (credentials from the VMS DB)."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import quote, urlparse, urlunparse


@dataclass
class OnvifStream:
    label: str
    url: str
    profile_token: str


@dataclass
class OnvifResult:
    streams: list[OnvifStream] = field(default_factory=list)
    port: int = 0
    error: str = ""


def onvif_ports(cam) -> list[int]:
    ports: list[int] = []
    for p in (cam.http_port, 80, 8999, 8899, 8000):
        try:
            pi = int(p)
        except (TypeError, ValueError):
            continue
        if pi > 0 and pi not in ports:
            ports.append(pi)
    return ports or [80]


def inject_rtsp_credentials(url: str, user: str, password: str) -> str:
    """ONVIF often returns RTSP URLs without embedded credentials."""

    url = (url or "").strip().replace("&amp;", "&")
    if not url.lower().startswith("rtsp://"):
        return url
    rest = url[7:]
    if "@" in rest:
        return url
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if not host:
        return url
    auth = f"{quote(user, safe='')}:{quote(password, safe='')}"
    netloc = auth + "@" + host
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse((
        parsed.scheme, netloc, parsed.path or "",
        parsed.params, parsed.query, parsed.fragment,
    ))


def discover_streams(cam, timeout: int = 8) -> list[OnvifStream]:
    result = discover_streams_verbose(cam, timeout=timeout)
    return result.streams


def discover_streams_verbose(cam, timeout: int = 8) -> OnvifResult:
    """Return RTSP URLs via ONVIF GetStreamUri, trying common ONVIF ports."""

    try:
        from onvif import ONVIFCamera
    except ImportError:
        return OnvifResult(error="onvif-zeep not installed — run: pip install onvif-zeep")

    last_err = ""
    for port in onvif_ports(cam):
        streams: list[OnvifStream] = []
        try:
            cli = ONVIFCamera(
                cam.ip,
                port,
                cam.user,
                cam.password,
                adjust_time=True,
            )
            if hasattr(cli, "update_xaddrs"):
                cli.update_xaddrs(timeout=timeout)
            media = cli.create_media_service()
            profiles = media.GetProfiles()
            for idx, prof in enumerate(profiles):
                token = prof.token
                label = getattr(prof, "Name", None) or f"profile-{idx}"
                resp = media.GetStreamUri({
                    "StreamSetup": {
                        "Stream": "RTP-Unicast",
                        "Transport": {"Protocol": "RTSP"},
                    },
                    "ProfileToken": token,
                })
                uri = inject_rtsp_credentials(
                    (resp.Uri or "").strip(), cam.user, cam.password,
                )
                if uri.lower().startswith("rtsp://"):
                    streams.append(OnvifStream(label=label, url=uri, profile_token=token))
            if streams:
                return OnvifResult(streams=streams, port=port)
            last_err = f"ONVIF port {port}: no RTSP profiles"
        except Exception as exc:
            last_err = f"ONVIF port {port}: {exc}"
    return OnvifResult(error=last_err or "ONVIF failed on all ports")
