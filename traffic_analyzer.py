"""Traffic analysis helpers for MikroTik user/session data."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from log_parser import LogEvent


def analyze_user_traffic(events: list[LogEvent], username: str = "") -> dict[str, Any]:
    """Summarize traffic patterns from parsed log events."""
    filtered = events
    if username:
        q = username.lower()
        filtered = [
            e
            for e in events
            if q in e.message.lower() or q in e.hostname.lower()
        ]

    src_ips: dict[str, int] = defaultdict(int)
    dst_ips: dict[str, int] = defaultdict(int)
    protocols: dict[str, int] = defaultdict(int)

    for ev in filtered:
        if ev.source_ip:
            src_ips[ev.source_ip] += 1
        if ev.dest_ip:
            dst_ips[ev.dest_ip] += 1
        if ev.protocol:
            protocols[ev.protocol] += 1

    return {
        "username": username or "all",
        "total_events": len(filtered),
        "source_ips": dict(sorted(src_ips.items(), key=lambda x: -x[1])[:20]),
        "dest_ips": dict(sorted(dst_ips.items(), key=lambda x: -x[1])[:20]),
        "protocols": dict(protocols),
    }


def build_flow_matrix(events: list[LogEvent]) -> list[dict[str, Any]]:
    """
    Build a 4D flow matrix for visualization:
    time × source × destination × service (size = count).
    """
    flows: dict[tuple, int] = defaultdict(int)
    for ev in events:
        key = (
            ev.timestamp.rsplit(":", 1)[0] if ":" in ev.timestamp else ev.timestamp,
            ev.source_ip or "?",
            ev.dest_ip or ev.dns_query or "?",
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
    """Extract DHCP lease lifecycle for Sankey/flow chart."""
    rows = []
    for ev in events:
        if ev.service != "dhcp":
            continue
        rows.append(
            {
                "time": ev.timestamp,
                "action": ev.dhcp_action or "event",
                "client": ev.source_ip or ev.client_mac or "?",
                "mac": ev.client_mac,
                "hostname": ev.hostname,
                "interface": ev.interface,
            }
        )
    return rows


def dns_resolution_map(events: list[LogEvent]) -> list[dict[str, Any]]:
    """Map DNS queries to resolving paths."""
    queries: dict[str, dict] = {}
    for ev in events:
        if ev.service != "dns" or not ev.dns_query:
            continue
        q = ev.dns_query
        if q not in queries:
            queries[q] = {"query": q, "count": 0, "clients": set(), "resolvers": set()}
        queries[q]["count"] += 1
        if ev.source_ip:
            queries[q]["clients"].add(ev.source_ip)
        if ev.dest_ip:
            queries[q]["resolvers"].add(ev.dest_ip)

    result = []
    for item in sorted(queries.values(), key=lambda x: -x["count"])[:50]:
        result.append(
            {
                "query": item["query"],
                "count": item["count"],
                "clients": list(item["clients"])[:10],
                "resolvers": list(item["resolvers"])[:5],
            }
        )
    return result
