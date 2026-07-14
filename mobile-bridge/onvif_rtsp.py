"""Discover camera RTSP URLs through ONVIF (same credentials as the VMS DB)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OnvifStream:
    label: str
    url: str
    profile_token: str


def discover_streams(cam, timeout: int = 8) -> list[OnvifStream]:
    """Return RTSP URLs advertised by the camera via ONVIF GetStreamUri."""

    try:
        from onvif import ONVIFCamera
    except ImportError:
        return []

    streams: list[OnvifStream] = []
    try:
        cli = ONVIFCamera(
            cam.ip,
            cam.http_port,
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
            uri = (resp.Uri or "").strip()
            if uri.lower().startswith("rtsp://"):
                streams.append(OnvifStream(label=label, url=uri, profile_token=token))
    except Exception:
        return []
    return streams
