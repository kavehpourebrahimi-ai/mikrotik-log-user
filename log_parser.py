"""Parse MikroTik RouterOS syslog lines into structured events."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LogEvent:
    timestamp: str
    topic: str
    message: str
    source_ip: str = ""
    dest_ip: str = ""
    protocol: str = ""
    service: str = ""
    client_mac: str = ""
    hostname: str = ""
    dns_query: str = ""
    dhcp_action: str = ""
    interface: str = ""
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# RouterOS syslog: "Jan/15/2024 14:30:45 dhcp,info ..." or with router prefix
SYSLOG_RE = re.compile(
    r"^(?:(\w{3}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})\s+)?"
    r"(?:(\w+(?:,\w+)*)\s+)?"
    r"(.*)$"
)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
MAC_RE = re.compile(r"\b([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\b")
DNS_QUERY_RE = re.compile(r"(?:query|resolved|cache)\s+(?:from\s+\S+\s+)?(?:for\s+)?([a-zA-Z0-9._-]+)", re.I)
DHCP_RE = re.compile(
    r"(dhcp(?:v6)?)\s+(offer|ack|request|decline|release|renew|assign|deassign|bound|conflict)",
    re.I,
)
PROTOCOL_RE = re.compile(r"\b(TCP|UDP|ICMP|IGMP|GRE|ESP|AH)\b", re.I)
INTERFACE_RE = re.compile(r"(?:in|out|on|via|interface)[:\s]+([\w.-]+)", re.I)


def _detect_service(topic: str, message: str) -> str:
    combined = f"{topic} {message}".lower()
    if "dhcp" in combined:
        return "dhcp"
    if any(k in combined for k in ("dns", "resolve", "cache")):
        return "dns"
    if "firewall" in combined or "drop" in combined or "accept" in combined:
        return "firewall"
    if "hotspot" in combined:
        return "hotspot"
    if "ppp" in combined or "l2tp" in combined or "pptp" in combined:
        return "vpn"
    if "wireless" in combined or "wifi" in combined:
        return "wireless"
    if "route" in combined or "bgp" in combined or "ospf" in combined:
        return "routing"
    return "system"


def parse_log_line(line: str, default_ts: str | None = None) -> LogEvent:
    """Parse a single MikroTik log line into a LogEvent."""
    line = line.strip()
    if not line:
        return LogEvent(
            timestamp=default_ts or datetime.now().isoformat(),
            topic="",
            message="",
            raw=line,
        )

    ts = default_ts or datetime.now().strftime("%b/%d/%Y %H:%M:%S")
    topic = ""
    message = line

    match = SYSLOG_RE.match(line)
    if match:
        if match.group(1):
            ts = match.group(1)
        if match.group(2):
            topic = match.group(2)
        if match.group(3):
            message = match.group(3)

    ips = IP_RE.findall(message)
    source_ip = ips[0] if ips else ""
    dest_ip = ips[1] if len(ips) > 1 else ""

    mac_match = MAC_RE.search(message)
    client_mac = mac_match.group(1).upper() if mac_match else ""

    dns_match = DNS_QUERY_RE.search(message)
    dns_query = dns_match.group(1) if dns_match else ""

    dhcp_match = DHCP_RE.search(message)
    dhcp_action = dhcp_match.group(2).lower() if dhcp_match else ""

    proto_match = PROTOCOL_RE.search(message)
    protocol = proto_match.group(1).upper() if proto_match else ""

    iface_match = INTERFACE_RE.search(message)
    interface = iface_match.group(1) if iface_match else ""

    service = _detect_service(topic, message)

    hostname = ""
    if service == "dhcp" and "host" in message.lower():
        host_match = re.search(r"host\s+([^\s,]+)", message, re.I)
        if host_match:
            hostname = host_match.group(1)

    return LogEvent(
        timestamp=ts,
        topic=topic,
        message=message,
        source_ip=source_ip,
        dest_ip=dest_ip,
        protocol=protocol,
        service=service,
        client_mac=client_mac,
        hostname=hostname,
        dns_query=dns_query,
        dhcp_action=dhcp_action,
        interface=interface,
        raw=line,
    )


def aggregate_events(events: list[LogEvent]) -> dict[str, Any]:
    """Build summary statistics for dashboard charts."""
    by_service: dict[str, int] = {}
    by_topic: dict[str, int] = {}
    dhcp_flow: list[dict[str, str]] = []
    dns_queries: dict[str, int] = {}
    ip_pairs: dict[str, int] = {}
    timeline: dict[str, int] = {}

    for ev in events:
        by_service[ev.service] = by_service.get(ev.service, 0) + 1
        if ev.topic:
            by_topic[ev.topic] = by_topic.get(ev.topic, 0) + 1

        if ev.service == "dhcp" and ev.dhcp_action:
            dhcp_flow.append(
                {
                    "timestamp": ev.timestamp,
                    "action": ev.dhcp_action,
                    "client_ip": ev.source_ip or ev.dest_ip,
                    "mac": ev.client_mac,
                    "hostname": ev.hostname,
                    "interface": ev.interface,
                    "message": ev.message[:120],
                }
            )

        if ev.service == "dns" and ev.dns_query:
            dns_queries[ev.dns_query] = dns_queries.get(ev.dns_query, 0) + 1

        if ev.source_ip and ev.dest_ip:
            pair = f"{ev.source_ip} → {ev.dest_ip}"
            ip_pairs[pair] = ip_pairs.get(pair, 0) + 1

        # Bucket by minute-ish key from timestamp
        time_key = ev.timestamp.rsplit(":", 1)[0] if ":" in ev.timestamp else ev.timestamp
        timeline[time_key] = timeline.get(time_key, 0) + 1

    top_dns = sorted(dns_queries.items(), key=lambda x: x[1], reverse=True)[:20]
    top_pairs = sorted(ip_pairs.items(), key=lambda x: x[1], reverse=True)[:20]

    return {
        "total": len(events),
        "by_service": by_service,
        "by_topic": by_topic,
        "dhcp_flow": dhcp_flow[-100:],
        "top_dns": [{"query": q, "count": c} for q, c in top_dns],
        "top_ip_pairs": [{"pair": p, "count": c} for p, c in top_pairs],
        "timeline": [{"time": t, "count": c} for t, c in sorted(timeline.items())],
    }
