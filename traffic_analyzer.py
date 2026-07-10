"""Traffic analysis helpers for MikroTik user/session data."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from log_parser import LogEvent, parse_timestamp


def filter_events(
    events: list[LogEvent],
    service: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    source_ip: str | None = None,
    dest_ip: str | None = None,
    username: str | None = None,
) -> list[LogEvent]:
    result = events
    if service:
        result = [e for e in result if e.service == service]
    if search:
        q = search.lower()
        result = [
            e
            for e in result
            if q in e.message.lower()
            or q in e.raw.lower()
            or q in e.dns_query.lower()
            or q in e.source_ip
            or q in e.dest_ip
            or q in e.username.lower()
        ]
    if source_ip:
        result = [e for e in result if source_ip in e.source_ip or source_ip in e.login_from_ip]
    if dest_ip:
        result = [
            e
            for e in result
            if dest_ip in e.dest_ip or dest_ip in e.dest_name or dest_ip in e.dns_query
        ]
    if username:
        result = [e for e in result if username.lower() in e.username.lower()]

    if date_from or date_to:
        dt_from = parse_timestamp(date_from) if date_from else None
        dt_to = parse_timestamp(date_to) if date_to else None
        filtered = []
        for e in result:
            dt = parse_timestamp(e.timestamp)
            if dt is None:
                filtered.append(e)
                continue
            if dt_from and dt < dt_from:
                continue
            if dt_to and dt > dt_to:
                continue
            filtered.append(e)
        result = filtered
    return result


def sort_events(
    events: list[LogEvent],
    sort_by: str = "timestamp",
    order: str = "desc",
) -> list[LogEvent]:
    reverse = order.lower() != "asc"

    def key_fn(e: LogEvent):
        if sort_by == "timestamp":
            dt = parse_timestamp(e.timestamp)
            return dt or e.timestamp
        return getattr(e, sort_by, "") or ""

    return sorted(events, key=key_fn, reverse=reverse)


def analyze_user_traffic(events: list[LogEvent], username: str = "") -> dict[str, Any]:
    filtered = filter_events(events, username=username) if username else events
    if username:
        q = username.lower()
        filtered = [e for e in filtered if q in e.message.lower() or q in e.username.lower() or q in e.hostname.lower()]

    src_ips: dict[str, int] = defaultdict(int)
    dst_ips: dict[str, int] = defaultdict(int)
    protocols: dict[str, int] = defaultdict(int)

    for ev in filtered:
        src = ev.source_ip or ev.login_from_ip
        dst = ev.dest_ip or ev.dest_name or ev.dns_query
        if src:
            src_ips[src] += 1
        if dst:
            dst_ips[dst] += 1
        if ev.protocol:
            protocols[ev.protocol] += 1

    return {
        "username": username or "all",
        "total_events": len(filtered),
        "source_ips": dict(sorted(src_ips.items(), key=lambda x: -x[1])[:30]),
        "dest_ips": dict(sorted(dst_ips.items(), key=lambda x: -x[1])[:30]),
        "protocols": dict(protocols),
    }


def build_flow_matrix(events: list[LogEvent]) -> list[dict[str, Any]]:
    flows: dict[tuple, int] = defaultdict(int)
    for ev in events:
        src = ev.source_ip or ev.login_from_ip or "?"
        dst = ev.dest_ip or ev.dest_name or ev.dns_query or "?"
        key = (
            ev.timestamp.rsplit(":", 1)[0] if ":" in ev.timestamp else ev.timestamp,
            src,
            dst,
            ev.service,
        )
        flows[key] += 1

    return [
        {
            "time": k[0],
            "source": k[1],
            "destination": k[2],
            "service": k[3],
            "count": v,
        }
        for k, v in sorted(flows.items(), key=lambda x: -x[1])[:500]
    ]


def dhcp_timeline(events: list[LogEvent]) -> list[dict[str, str]]:
    rows = []
    for ev in events:
        if ev.service != "dhcp":
            continue
        rows.append(
            {
                "time": ev.timestamp,
                "action": ev.dhcp_action or "event",
                "source_ip": ev.source_ip,
                "dest_ip": ev.dest_ip,
                "client": ev.source_ip or ev.client_mac or "?",
                "mac": ev.client_mac,
                "hostname": ev.hostname,
                "interface": ev.interface,
            }
        )
    return rows


def dns_resolution_map(events: list[LogEvent]) -> list[dict[str, Any]]:
    queries: dict[str, dict] = {}
    for ev in events:
        if ev.service != "dns" or not ev.dns_query:
            continue
        q = ev.dns_query
        if q not in queries:
            queries[q] = {
                "query": q,
                "count": 0,
                "clients": set(),
                "resolvers": set(),
                "resolved_ips": set(),
            }
        queries[q]["count"] += 1
        if ev.source_ip:
            queries[q]["clients"].add(ev.source_ip)
        if ev.dest_ip:
            queries[q]["resolvers"].add(ev.dest_ip)
            queries[q]["resolved_ips"].add(ev.dest_ip)

    result = []
    for item in sorted(queries.values(), key=lambda x: -x["count"])[:50]:
        result.append(
            {
                "query": item["query"],
                "count": item["count"],
                "source_ips": list(item["clients"])[:10],
                "dest_ips": list(item["resolved_ips"])[:10],
                "resolvers": list(item["resolvers"])[:5],
            }
        )
    return result


def vpn_sessions(events: list[LogEvent]) -> list[dict[str, Any]]:
    """PPP/PPTP/L2TP sessions with source and destination addresses."""
    rows = []
    for ev in events:
        if ev.service != "vpn":
            continue
        rows.append(
            {
                "time": ev.timestamp,
                "username": ev.username,
                "vpn_type": ev.vpn_type or "ppp",
                "action": ev.action,
                "source_ip": ev.source_ip or ev.login_from_ip,
                "dest_ip": ev.dest_ip,
                "interface": ev.interface,
                "message": ev.message[:150],
            }
        )
    return rows


def vpn_summary(events: list[LogEvent]) -> dict[str, Any]:
    by_user: dict[str, dict] = {}
    by_type: dict[str, int] = defaultdict(int)
    src_map: dict[str, int] = defaultdict(int)
    dst_map: dict[str, int] = defaultdict(int)

    for ev in events:
        if ev.service != "vpn":
            continue
        by_type[ev.vpn_type or "ppp"] += 1
        src = ev.source_ip or ev.login_from_ip
        if src:
            src_map[src] += 1
        if ev.dest_ip:
            dst_map[ev.dest_ip] += 1
        user = ev.username or "unknown"
        if user not in by_user:
            by_user[user] = {"username": user, "count": 0, "source_ips": set(), "dest_ips": set(), "vpn_types": set()}
        by_user[user]["count"] += 1
        if src:
            by_user[user]["source_ips"].add(src)
        if ev.dest_ip:
            by_user[user]["dest_ips"].add(ev.dest_ip)
        if ev.vpn_type:
            by_user[user]["vpn_types"].add(ev.vpn_type)

    users = []
    for u in sorted(by_user.values(), key=lambda x: -x["count"])[:30]:
        users.append(
            {
                "username": u["username"],
                "count": u["count"],
                "source_ips": list(u["source_ips"]),
                "dest_ips": list(u["dest_ips"]),
                "vpn_types": list(u["vpn_types"]),
            }
        )

    return {
        "total": sum(by_type.values()),
        "by_type": dict(by_type),
        "top_source_ips": dict(sorted(src_map.items(), key=lambda x: -x[1])[:20]),
        "top_dest_ips": dict(sorted(dst_map.items(), key=lambda x: -x[1])[:20]),
        "users": users,
        "sessions": vpn_sessions(events)[-100:],
    }


def hotspot_activity(events: list[LogEvent]) -> dict[str, Any]:
    by_user: dict[str, dict] = {}
    rows = []
    for ev in events:
        if ev.service != "hotspot":
            continue
        rows.append(
            {
                "time": ev.timestamp,
                "username": ev.username,
                "action": ev.action,
                "source_ip": ev.source_ip or ev.login_from_ip,
                "dest_ip": ev.dest_ip,
                "mac": ev.client_mac,
                "message": ev.message[:150],
            }
        )
        user = ev.username or ev.source_ip or "unknown"
        if user not in by_user:
            by_user[user] = {"username": user, "logins": 0, "logouts": 0, "source_ips": set(), "events": 0}
        by_user[user]["events"] += 1
        if ev.action in ("login", "logged in"):
            by_user[user]["logins"] += 1
        elif ev.action in ("logout", "logged out"):
            by_user[user]["logouts"] += 1
        if ev.source_ip:
            by_user[user]["source_ips"].add(ev.source_ip)

    users = [
        {
            "username": u["username"],
            "logins": u["logins"],
            "logouts": u["logouts"],
            "events": u["events"],
            "source_ips": list(u["source_ips"]),
        }
        for u in sorted(by_user.values(), key=lambda x: -x["events"])[:50]
    ]

    return {"total": len(rows), "users": users, "events": rows[-200:]}


def login_audit(events: list[LogEvent]) -> dict[str, Any]:
    """Who logged into MikroTik, from which IP, how many times."""
    by_user: dict[str, dict] = {}
    by_ip: dict[str, int] = defaultdict(int)
    rows = []

    for ev in events:
        is_login = ev.service == "login" or (
            ev.service == "system" and any(k in ev.message.lower() for k in ("logged in", "login", "logged out", "authentication"))
        )
        if not is_login:
            continue

        user = ev.username
        if not user:
            um = re.search(r"user\s+([^\s]+)", ev.message, re.I)
            user = um.group(1) if um else "admin"

        from_ip = ev.login_from_ip or ev.source_ip or "?"
        rows.append(
            {
                "time": ev.timestamp,
                "username": user,
                "action": ev.action or "login",
                "source_ip": from_ip,
                "message": ev.message[:150],
            }
        )

        if user not in by_user:
            by_user[user] = {"username": user, "count": 0, "source_ips": defaultdict(int), "last_seen": ev.timestamp}
        by_user[user]["count"] += 1
        by_user[user]["source_ips"][from_ip] += 1
        by_user[user]["last_seen"] = ev.timestamp
        by_ip[from_ip] += 1

    users = []
    for u in sorted(by_user.values(), key=lambda x: -x["count"]):
        users.append(
            {
                "username": u["username"],
                "login_count": u["count"],
                "last_seen": u["last_seen"],
                "source_ips": [
                    {"ip": ip, "count": cnt}
                    for ip, cnt in sorted(u["source_ips"].items(), key=lambda x: -x[1])
                ],
            }
        )

    return {
        "total_logins": len(rows),
        "users": users,
        "top_source_ips": [{"ip": ip, "count": c} for ip, c in sorted(by_ip.items(), key=lambda x: -x[1])[:20]],
        "events": rows[-200:],
    }
