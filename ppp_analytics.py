"""PPP/VPN analytics — L2TP, SSTP, IPIP, PPTP, OVPN sessions with traffic & uptime."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from log_database import log_db


VPN_SERVICES = ("l2tp", "sstp", "pptp", "pppoe", "ovpn", "openvpn", "ipip", "gre", "eoip")


def _normalize_ppp_session(raw: dict[str, str]) -> dict[str, Any]:
    """Normalize RouterOS /ppp/active detail record."""
    service = (raw.get("service") or raw.get("type") or "unknown").lower()
    bytes_in = raw.get("limit-bytes-in") or raw.get("bytes-in") or "0"
    bytes_out = raw.get("limit-bytes-out") or raw.get("bytes-out") or "0"

    return {
        "username": raw.get("name", raw.get("user", "")),
        "service": service,
        "service_label": service.upper(),
        "address": raw.get("address", ""),
        "caller_id": raw.get("caller-id", raw.get("caller_id", "")),
        "uptime": raw.get("uptime", ""),
        "encoding": raw.get("encoding", ""),
        "session_id": raw.get(".id", raw.get("session-id", "")),
        "radius": raw.get("radius", "false") == "true",
        "bytes_in": bytes_in,
        "bytes_out": bytes_out,
        "interface": raw.get("interface", ""),
        "active": True,
    }


def fetch_and_store_ppp_sessions(conn) -> list[dict[str, Any]]:
    """Pull live PPP sessions from MikroTik and persist snapshot."""
    raw = conn.fetch_ppp_active()
    sessions = [_normalize_ppp_session(r) for r in raw]
    log_db.save_ppp_snapshot(conn.host, sessions)
    return sessions


def fetch_and_store_hotspot_sessions(conn) -> list[dict[str, Any]]:
    raw = conn.fetch_hotspot_active()
    sessions = []
    for r in raw:
        sessions.append(
            {
                "username": r.get("user", r.get("user-name", "")),
                "address": r.get("address", ""),
                "mac": r.get("mac-address", r.get("mac_address", "")),
                "uptime": r.get("uptime", ""),
                "bytes_in": r.get("bytes-in", r.get("bytes_in", "")),
                "bytes_out": r.get("bytes-out", r.get("bytes_out", "")),
                "login_by": r.get("login-by", ""),
                "active": True,
            }
        )
    log_db.save_hotspot_snapshot(conn.host, sessions)
    return sessions


def build_ppp_report(
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Full PPP/VPN report: live sessions + historical logs."""
    live = log_db.latest_ppp_snapshot()
    events = log_db.query_events(
        service="vpn",
        limit=10000,
        date_from=date_from,
        date_to=date_to,
        sort_by="id",
        sort_order="DESC",
    )

    by_service: dict[str, list] = defaultdict(list)
    for s in live:
        svc = s.get("service", "unknown")
        by_service[svc].append(s)

    # Historical from logs
    log_by_user: dict[str, dict] = {}
    for ev in events:
        user = ev.get("username") or "unknown"
        if user not in log_by_user:
            log_by_user[user] = {
                "username": user,
                "events": 0,
                "vpn_types": set(),
                "source_ips": set(),
                "dest_ips": set(),
                "last_action": "",
                "last_time": "",
            }
        log_by_user[user]["events"] += 1
        if ev.get("vpn_type"):
            log_by_user[user]["vpn_types"].add(ev["vpn_type"])
        if ev.get("source_ip"):
            log_by_user[user]["source_ips"].add(ev["source_ip"])
        if ev.get("dest_ip"):
            log_by_user[user]["dest_ips"].add(ev["dest_ip"])
        log_by_user[user]["last_action"] = ev.get("action", "")
        log_by_user[user]["last_time"] = ev.get("timestamp", "")

    history = []
    for u in log_by_user.values():
        history.append(
            {
                **u,
                "vpn_types": sorted(u["vpn_types"]),
                "source_ips": sorted(u["source_ips"]),
                "dest_ips": sorted(u["dest_ips"]),
            }
        )
    history.sort(key=lambda x: -x["events"])

    # Count by VPN type from logs
    type_counts: dict[str, int] = defaultdict(int)
    for ev in events:
        vt = (ev.get("vpn_type") or "ppp").lower()
        type_counts[vt] += 1
    for s in live:
        type_counts[s.get("service", "unknown")] += 1

    return {
        "active_count": len(live),
        "active_sessions": live,
        "by_service": {k: v for k, v in by_service.items()},
        "service_summary": dict(type_counts),
        "historical_users": history[:100],
        "recent_log_events": events[:200],
    }


def detect_vpn_type_from_message(message: str) -> str:
    msg = message.lower()
    for svc in VPN_SERVICES:
        if svc in msg:
            return svc
    return "ppp"
