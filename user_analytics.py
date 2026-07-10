"""User-centric analytics — FortiAnalyzer-style user log aggregation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from log_database import log_db


def _bytes_fmt(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} PB"


def build_users_report(
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Aggregate all log events per username across VPN, Hotspot, login, etc."""
    events = log_db.query_events(
        limit=50000,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )

    users: dict[str, dict] = {}
    for ev in events:
        name = (ev.get("username") or "").strip()
        if not name:
            # Try extract from message for hotspot/ppp
            msg = ev.get("message", "")
            if "user=" in msg.lower():
                import re
                m = re.search(r"user[=:\s]+([^\s,;]+)", msg, re.I)
                name = m.group(1) if m else ""
        if not name:
            continue

        if name not in users:
            users[name] = {
                "username": name,
                "total_logs": 0,
                "services": defaultdict(int),
                "source_ips": set(),
                "dest_ips": set(),
                "vpn_types": set(),
                "last_seen": ev.get("timestamp", ""),
                "first_seen": ev.get("timestamp", ""),
                "actions": defaultdict(int),
            }

        u = users[name]
        u["total_logs"] += 1
        svc = ev.get("service") or "system"
        u["services"][svc] += 1
        if ev.get("source_ip"):
            u["source_ips"].add(ev["source_ip"])
        if ev.get("login_from_ip"):
            u["source_ips"].add(ev["login_from_ip"])
        if ev.get("dest_ip"):
            u["dest_ips"].add(ev["dest_ip"])
        if ev.get("vpn_type"):
            u["vpn_types"].add(ev["vpn_type"])
        if ev.get("action"):
            u["actions"][ev["action"]] += 1
        u["last_seen"] = ev.get("timestamp") or u["last_seen"]
        ts = ev.get("timestamp") or ""
        if ts and (not u["first_seen"] or ts < u["first_seen"]):
            u["first_seen"] = ts

    # Merge live hotspot + ppp snapshot data
    hs_sessions = log_db.latest_hotspot_snapshot()
    ppp_sessions = log_db.latest_ppp_snapshot()
    hs_by_user = {s.get("user", s.get("user-name", "")): s for s in hs_sessions}
    ppp_by_user = {s.get("name", ""): s for s in ppp_sessions}

    result = []
    for name, u in users.items():
        hs = hs_by_user.get(name, {})
        ppp = ppp_by_user.get(name, {})
        result.append(
            {
                "username": name,
                "total_logs": u["total_logs"],
                "services": dict(u["services"]),
                "source_ips": sorted(u["source_ips"]),
                "dest_ips": sorted(u["dest_ips"])[:20],
                "vpn_types": sorted(u["vpn_types"]),
                "actions": dict(u["actions"]),
                "first_seen": u["first_seen"],
                "last_seen": u["last_seen"],
                "hotspot_active": bool(hs),
                "hotspot_uptime": hs.get("uptime", ""),
                "hotspot_bytes_in": hs.get("bytes-in", hs.get("bytes_in", "")),
                "hotspot_bytes_out": hs.get("bytes-out", hs.get("bytes_out", "")),
                "hotspot_address": hs.get("address", ""),
                "ppp_active": bool(ppp),
                "ppp_service": ppp.get("service", ""),
                "ppp_uptime": ppp.get("uptime", ""),
                "ppp_caller_id": ppp.get("caller-id", ppp.get("caller_id", "")),
                "ppp_address": ppp.get("address", ""),
            }
        )

    result.sort(key=lambda x: -x["total_logs"])
    return {"total_users": len(result), "users": result[:limit]}


def user_detail(username: str, limit: int = 500) -> dict[str, Any]:
    """All logs for a specific user."""
    events = log_db.query_events(username=username, limit=limit, sort_by="id", sort_order="DESC")
    report = build_users_report()
    user_info = next((u for u in report["users"] if u["username"] == username), {})
    return {"user": user_info, "logs": events, "log_count": len(events)}
