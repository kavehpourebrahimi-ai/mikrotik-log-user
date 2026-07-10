"""Parse MikroTik RouterOS syslog lines into structured events."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
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
    username: str = ""
    vpn_type: str = ""
    action: str = ""
    dest_name: str = ""
    login_from_ip: str = ""
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SYSLOG_RE = re.compile(
    r"^(?:(\w{3}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})\s+)?"
    r"(?:(\w+(?:,\w+)*)\s+)?"
    r"(.*)$"
)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
MAC_RE = re.compile(r"\b([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\b")
DNS_QUERY_RE = re.compile(
    r"(?:query|resolved|cache|answer)\s+(?:from\s+(\d+\.\d+\.\d+\.\d+)\s+)?(?:for\s+)?([a-zA-Z0-9._*-]+)",
    re.I,
)
DNS_RESOLVED_RE = re.compile(r"(?:resolved|answer|cache).*?(\d+\.\d+\.\d+\.\d+)", re.I)
DHCP_RE = re.compile(
    r"(?:dhcp(?:v6)?)\s+(offer|ack|request|decline|release|renew|assign|deassign|bound|conflict)",
    re.I,
)
PROTOCOL_RE = re.compile(r"\b(TCP|UDP|ICMP|IGMP|GRE|ESP|AH)\b", re.I)
INTERFACE_RE = re.compile(r"(?:in|out|on|via|interface)[:\s]+([\w<>\-/]+)", re.I)
FIREWALL_PAIR_RE = re.compile(
    r"(?:src|source)[-:]?\s*address[=:]?\s*(\d+\.\d+\.\d+\.\d+).*?(?:dst|dest)[-:]?\s*address[=:]?\s*(\d+\.\d+\.\d+\.\d+)",
    re.I,
)
USER_RE = re.compile(r"(?:user|username)[=:\s]+([^\s,;]+)", re.I)
LOGIN_RE = re.compile(
    r"(logged in|login|logged out|logout|authentication failed|connected|disconnected)\s*(?:from|via|by)?\s*(\d+\.\d+\.\d+\.\d+)?",
    re.I,
)
VPN_TYPE_RE = re.compile(r"\b(pptp|l2tp|pppoe|sstp|ovpn|openvpn|ipsec|ike)\b", re.I)
HOTSPOT_RE = re.compile(
    r"(logged in|logged out|login|logout|trial|mac).*?(?:user[=:\s]+([^\s,]+))?",
    re.I,
)
PPP_CONN_RE = re.compile(
    r"<([^>]+)>\s*(?:connected|disconnected).*?(?:from|local|remote)[=:\s]+(\d+\.\d+\.\d+\.\d+).*?(?:to|remote)[=:\s]+(\d+\.\d+\.\d+\.\d+)?",
    re.I,
)


def _detect_service(topic: str, message: str) -> str:
    combined = f"{topic} {message}".lower()
    if "account" in combined or "login" in combined or "system,info,account" in combined:
        return "login"
    if "dhcp" in combined:
        return "dhcp"
    if any(k in combined for k in ("dns", "resolve", "cache")):
        return "dns"
    if "firewall" in combined or "drop" in combined or "accept" in combined:
        return "firewall"
    if "hotspot" in combined:
        return "hotspot"
    if any(k in combined for k in ("ppp", "l2tp", "pptp", "pppoe", "sstp", "ovpn")):
        return "vpn"
    if "wireless" in combined or "wifi" in combined:
        return "wireless"
    if "route" in combined or "bgp" in combined or "ospf" in combined:
        return "routing"
    return "system"


def _extract_ips(message: str, service: str) -> tuple[str, str]:
    fw = FIREWALL_PAIR_RE.search(message)
    if fw:
        return fw.group(1), fw.group(2)

    ppp = PPP_CONN_RE.search(message)
    if ppp:
        return ppp.group(2) or "", ppp.group(3) or ""

    ips = IP_RE.findall(message)
    if service == "dns":
        dns_m = DNS_QUERY_RE.search(message)
        if dns_m and dns_m.group(1):
            return dns_m.group(1), ""
        if len(ips) >= 2:
            return ips[0], ips[1]
        return ips[0] if ips else "", ""

    if service == "login":
        login_m = LOGIN_RE.search(message)
        if login_m and login_m.group(2):
            return login_m.group(2), ""
        return ips[0] if ips else "", ips[1] if len(ips) > 1 else ""

    if len(ips) >= 2:
        return ips[0], ips[1]
    return ips[0] if ips else "", ""


def parse_log_line(line: str, default_ts: str | None = None) -> LogEvent:
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

    service = _detect_service(topic, message)
    source_ip, dest_ip = _extract_ips(message, service)

    mac_match = MAC_RE.search(message)
    client_mac = mac_match.group(1).upper() if mac_match else ""

    dns_query = ""
    dest_name = ""
    dns_match = DNS_QUERY_RE.search(message)
    if dns_match:
        dns_query = dns_match.group(2) or ""
        dest_name = dns_query
    resolved = DNS_RESOLVED_RE.search(message)
    if resolved and not dest_ip:
        dest_ip = resolved.group(1)

    dhcp_match = DHCP_RE.search(message)
    dhcp_action = dhcp_match.group(1).lower() if dhcp_match else ""

    proto_match = PROTOCOL_RE.search(message)
    protocol = proto_match.group(1).upper() if proto_match else ""

    iface_match = INTERFACE_RE.search(message)
    interface = iface_match.group(1) if iface_match else ""

    username = ""
    user_match = USER_RE.search(message)
    if user_match:
        username = user_match.group(1)

    vpn_type = ""
    vpn_match = VPN_TYPE_RE.search(message)
    if vpn_match:
        vpn_type = vpn_match.group(1).lower()

    action = ""
    login_from_ip = ""
    login_match = LOGIN_RE.search(message)
    if login_match:
        action = login_match.group(1).lower()
        login_from_ip = login_match.group(2) or source_ip
    elif dhcp_action:
        action = dhcp_action
    elif "connected" in message.lower():
        action = "connected"
    elif "disconnected" in message.lower():
        action = "disconnected"

    if service == "hotspot":
        hs = HOTSPOT_RE.search(message)
        if hs and hs.group(2):
            username = hs.group(2)
        if "logged in" in message.lower() or "login" in message.lower():
            action = action or "login"
        elif "logged out" in message.lower() or "logout" in message.lower():
            action = action or "logout"

    if service == "vpn" and not username:
        ppp_user = re.search(r"<([^>]+)>", message)
        if ppp_user:
            username = ppp_user.group(1)

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
        username=username,
        vpn_type=vpn_type,
        action=action,
        dest_name=dest_name or dns_query,
        login_from_ip=login_from_ip,
        raw=line,
    )


def parse_timestamp(ts: str) -> datetime | None:
    """Best-effort parse of RouterOS timestamp."""
    for fmt in ("%b/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return None


def aggregate_events(events: list[LogEvent]) -> dict[str, Any]:
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

        src = ev.source_ip or ev.login_from_ip
        dst = ev.dest_ip or ev.dest_name or ev.dns_query
        if src and dst:
            pair = f"{src} → {dst}"
            ip_pairs[pair] = ip_pairs.get(pair, 0) + 1

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
