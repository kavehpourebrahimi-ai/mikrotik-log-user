"""IPIP / GRE / EoIP tunnel analytics — traffic between MikroTik peers."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from log_database import log_db

TUNNEL_TYPES = ("ipip", "gre", "eoip")


def _normalize_tunnel(raw: dict[str, str], tunnel_type: str, stats: dict[str, str] | None = None) -> dict[str, Any]:
    name = raw.get("name", "")
    stats = stats or {}
    return {
        "name": name,
        "type": tunnel_type,
        "type_label": tunnel_type.upper(),
        "local_address": raw.get("local-address", raw.get("local_address", "")),
        "remote_address": raw.get("remote-address", raw.get("remote_address", "")),
        "disabled": raw.get("disabled", "false") == "true",
        "running": raw.get("running", "false") == "true",
        "mtu": raw.get("mtu", ""),
        "comment": raw.get("comment", ""),
        "rx_bytes": stats.get("rx-byte", stats.get("rx_bytes", "0")),
        "tx_bytes": stats.get("tx-byte", stats.get("tx_bytes", "0")),
        "rx_packets": stats.get("rx-packet", stats.get("rx_packets", "0")),
        "tx_packets": stats.get("tx-packet", stats.get("tx_packets", "0")),
        "active": raw.get("running", "false") == "true",
    }


def fetch_and_store_tunnels(conn) -> list[dict[str, Any]]:
    """Pull IPIP/GRE/EoIP tunnels + interface traffic stats from MikroTik."""
    tunnels: list[dict[str, Any]] = []
    stats_map = conn.fetch_interface_stats()

    for ttype, fetch_fn in (
        ("ipip", conn.fetch_ipip_tunnels),
        ("gre", conn.fetch_gre_tunnels),
        ("eoip", conn.fetch_eoip_tunnels),
    ):
        for raw in fetch_fn():
            name = raw.get("name", "")
            tunnels.append(_normalize_tunnel(raw, ttype, stats_map.get(name, {})))

    log_db.save_tunnel_snapshot(conn.host, tunnels)
    return tunnels


def _is_tunnel_log(ev: dict) -> bool:
    svc = (ev.get("service") or "").lower()
    if svc == "tunnel":
        return True
    iface = (ev.get("interface") or "").lower()
    msg = (ev.get("message") or "").lower()
    vt = (ev.get("vpn_type") or "").lower()
    return any(t in iface or t in msg or t in vt for t in TUNNEL_TYPES)


def build_tunnel_report(
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """
    Report for IPIP/GRE/EoIP — shows peer links and traffic between MikroTik routers.
    Works when both routers send syslog to the same collector.
    """
    all_snapshots = log_db.all_tunnel_snapshots()
    events = log_db.query_events(
        limit=50000,
        date_from=date_from,
        date_to=date_to,
        sort_by="id",
        sort_order="DESC",
    )
    tunnel_logs = [ev for ev in events if _is_tunnel_log(ev)]

    # Build peer links from live tunnel config
    peer_links: list[dict[str, Any]] = []
    routers_seen: dict[str, list[dict]] = {}

    for snap in all_snapshots:
        router_ip = snap["router_ip"]
        routers_seen[router_ip] = snap["tunnels"]
        for t in snap["tunnels"]:
            peer_links.append({
                "router": router_ip,
                "tunnel_name": t["name"],
                "tunnel_type": t["type_label"],
                "local_address": t["local_address"],
                "peer_address": t["remote_address"],
                "running": t["running"],
                "rx_bytes": t["rx_bytes"],
                "tx_bytes": t["tx_bytes"],
                "rx_packets": t["rx_packets"],
                "tx_packets": t["tx_packets"],
                "comment": t.get("comment", ""),
            })

    # Match peers: Router A remote-address == Router B's public IP (router field)
    matched_pairs: list[dict[str, Any]] = []
    for link in peer_links:
        peer_ip = link["peer_address"]
        opposite = None
        for other_router, other_tunnels in routers_seen.items():
            if other_router == link["router"]:
                continue
            if other_router == peer_ip:
                opposite = other_router
                break
            for ot in other_tunnels:
                if ot["remote_address"] == link["router"] or ot["local_address"] and peer_ip in (ot["local_address"], ot["remote_address"]):
                    opposite = other_router
                    break
        matched_pairs.append({
            **link,
            "peer_router": opposite or peer_ip,
            "rx_formatted": _fmt_bytes(int(link.get("rx_bytes") or 0)),
            "tx_formatted": _fmt_bytes(int(link.get("tx_bytes") or 0)),
        })

    # Traffic flows through tunnel interfaces (from firewall/syslog)
    flow_counts: dict[str, dict] = {}
    for ev in tunnel_logs:
        iface = ev.get("interface") or ""
        src = ev.get("source_ip") or "?"
        dst = ev.get("dest_ip") or "?"
        router = ev.get("router_ip") or "?"
        key = f"{router}|{iface}|{src}->{dst}"
        if key not in flow_counts:
            flow_counts[key] = {
                "router": router,
                "interface": iface,
                "source_ip": src,
                "dest_ip": dst,
                "tunnel_type": ev.get("vpn_type") or "ipip",
                "count": 0,
                "protocol": ev.get("protocol", ""),
                "last_time": ev.get("timestamp", ""),
            }
        flow_counts[key]["count"] += 1

    flows = sorted(flow_counts.values(), key=lambda x: -x["count"])[:200]

    # Aggregate traffic bytes per tunnel from snapshots
    traffic_summary = []
    for link in peer_links:
        try:
            rx = int(link.get("rx_bytes") or 0)
            tx = int(link.get("tx_bytes") or 0)
        except ValueError:
            rx = tx = 0
        traffic_summary.append({
            **link,
            "total_bytes": rx + tx,
            "total_formatted": _fmt_bytes(rx + tx),
            "rx_formatted": _fmt_bytes(rx),
            "tx_formatted": _fmt_bytes(tx),
        })

    type_counts: dict[str, int] = defaultdict(int)
    for t in peer_links:
        type_counts[t["tunnel_type"]] += 1

    return {
        "tunnel_count": len(peer_links),
        "active_tunnels": sum(1 for t in peer_links if t["running"]),
        "routers": list(routers_seen.keys()),
        "peer_links": matched_pairs,
        "traffic_summary": traffic_summary,
        "traffic_flows": flows,
        "recent_tunnel_logs": tunnel_logs[:150],
        "type_summary": dict(type_counts),
        "log_count": len(tunnel_logs),
    }


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n //= 1024
    return f"{n} TB"
