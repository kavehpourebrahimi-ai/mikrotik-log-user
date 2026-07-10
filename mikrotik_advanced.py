"""SSH connection and data retrieval from MikroTik RouterOS."""

from __future__ import annotations

import re
import socket
from pathlib import Path
from typing import Any

import paramiko

import config


class MikroTikConnection:
    """Manage SSH sessions to MikroTik RouterOS."""

    def __init__(
        self,
        host: str | None = None,
        user: str | None = None,
        password: str | None = None,
        port: int | None = None,
    ):
        self.host = host or config.MIKROTIK_HOST
        self.user = user or config.MIKROTIK_USER
        self.password = password or config.MIKROTIK_PASSWORD
        self.port = port or config.MIKROTIK_PORT
        self._client: paramiko.SSHClient | None = None

    def connect(self) -> None:
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(
            self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            timeout=15,
            look_for_keys=False,
            allow_agent=False,
        )

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def run(self, command: str) -> str:
        if not self._client:
            self.connect()
        assert self._client is not None
        _, stdout, stderr = self._client.exec_command(command, timeout=30)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return out if out.strip() else err

    def fetch_logs(self, count: int = 500, topics: str = "") -> list[str]:
        """Pull recent logs from RouterOS via SSH."""
        where = f' where topics~"{topics}"' if topics else ""
        cmd = f"/log print count={count}{where}"
        output = self.run(cmd)
        return _parse_ros_table(output)

    def fetch_users(self) -> list[dict[str, str]]:
        """Fetch hotspot/PPP users if available."""
        output = self.run("/ip/hotspot/user/print detail")
        users = _parse_ros_detail(output)
        if not users:
            output = self.run("/ppp/secret/print detail")
            users = _parse_ros_detail(output)
        return users

    def fetch_connections(self) -> list[dict[str, str]]:
        output = self.run("/ip/firewall/connection/print")
        return _parse_ros_table_as_dicts(output)

    def fetch_dhcp_leases(self) -> list[dict[str, str]]:
        output = self.run("/ip/dhcp-server/lease/print detail")
        return _parse_ros_detail(output)

    def fetch_dns_cache(self) -> list[dict[str, str]]:
        output = self.run("/ip/dns/cache/print")
        return _parse_ros_table_as_dicts(output)

    def fetch_ppp_active(self) -> list[dict[str, str]]:
        output = self.run("/ppp/active/print detail")
        return _parse_ros_detail(output)

    def fetch_hotspot_active(self) -> list[dict[str, str]]:
        output = self.run("/ip/hotspot/active/print detail")
        return _parse_ros_detail(output)

    def fetch_hotspot_users(self) -> list[dict[str, str]]:
        output = self.run("/ip/hotspot/user/print detail")
        return _parse_ros_detail(output)

    def fetch_ppp_secrets(self) -> list[dict[str, str]]:
        output = self.run("/ppp/secret/print detail")
        return _parse_ros_detail(output)

    def fetch_ipip_peers(self) -> list[dict[str, str]]:
        return self.fetch_ipip_tunnels()

    def fetch_ipip_tunnels(self) -> list[dict[str, str]]:
        try:
            output = self.run("/interface/ipip/print detail")
            return _parse_ros_detail(output)
        except Exception:
            return []

    def fetch_gre_tunnels(self) -> list[dict[str, str]]:
        try:
            output = self.run("/interface/gre/print detail")
            return _parse_ros_detail(output)
        except Exception:
            return []

    def fetch_eoip_tunnels(self) -> list[dict[str, str]]:
        try:
            output = self.run("/interface/eoip/print detail")
            return _parse_ros_detail(output)
        except Exception:
            return []

    def fetch_interface_stats(self) -> dict[str, dict[str, str]]:
        """RX/TX bytes per interface — for IPIP tunnel traffic measurement."""
        try:
            output = self.run("/interface print stats")
            return _parse_interface_stats(output)
        except Exception:
            return {}

    def configure_remote_syslog(self, remote_ip: str, port: int = 514) -> str:
        """Configure MikroTik to forward ALL logs needed for FortiAnalyzer-style analysis."""
        commands = [
            f'/system logging action set [find name=remote] remote={remote_ip} remote-port={port} target=remote bsd-syslog=yes syslog-facility=daemon syslog-time-format=iso8601',
            '/system logging add action=remote topics=info,warning,error,critical',
            '/system logging add action=remote topics=account',
            '/system logging add action=remote topics=dhcp',
            '/system logging add action=remote topics=dns',
            '/system logging add action=remote topics=firewall',
            '/system logging add action=remote topics=hotspot',
            '/system logging add action=remote topics=ppp',
            '/system logging add action=remote topics=wireless',
            '/system logging add action=remote topics=system',
            '/system logging add action=remote topics=route',
            '/system logging add action=remote topics=debug',
            '/system logging add action=remote topics=event',
            '/system logging add action=remote topics=script',
            '/system logging add action=remote topics=ups',
        ]
        results = []
        for cmd in commands:
            try:
                results.append(self.run(cmd))
            except Exception as exc:
                results.append(str(exc))
        return "\n".join(results)

    @staticmethod
    def syslog_setup_script(remote_ip: str, port: int = 514) -> str:
        rsc = Path(__file__).parent / "mikrotik" / "full-logging-setup.rsc"
        if rsc.exists():
            return rsc.read_text(encoding="utf-8").replace("SERVER_IP", remote_ip).replace("SERVER_PORT", str(port))
        return f'/system logging action set [find name=remote] remote={remote_ip} remote-port={port} target=remote'

    def get_identity(self) -> dict[str, str]:
        output = self.run("/system/identity/print")
        rows = _parse_ros_table_as_dicts(output)
        return rows[0] if rows else {"name": self.host}

    def ping(self) -> bool:
        try:
            sock = socket.create_connection((self.host, self.port), timeout=5)
            sock.close()
            return True
        except OSError:
            return False


def _parse_ros_table(output: str) -> list[str]:
    """Extract log message lines from RouterOS print output."""
    lines = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or re.match(r"^\d+$", line):
            continue
        # Strip leading row number
        cleaned = re.sub(r"^\d+\s+", "", line)
        if cleaned:
            lines.append(cleaned)
    return lines


def _parse_ros_detail(output: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d+$", line) and current:
            records.append(current)
            current = {}
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            current[key.strip()] = val.strip()
    if current:
        records.append(current)
    return records


def _parse_ros_table_as_dicts(output: str) -> list[dict[str, str]]:
    """Best-effort parse of RouterOS tabular output."""
    lines = [l.strip() for l in output.splitlines() if l.strip() and not l.strip().startswith("#")]
    if len(lines) < 2:
        return []
    headers = re.split(r"\s{2,}", lines[0])
    rows = []
    for line in lines[1:]:
        if re.match(r"^\d+$", line):
            continue
        vals = re.split(r"\s{2,}", line, maxsplit=len(headers) - 1)
        if len(vals) >= len(headers):
            rows.append(dict(zip(headers, vals)))
    return rows


def _parse_interface_stats(output: str) -> dict[str, dict[str, str]]:
    """Parse /interface print stats into {name: {rx-byte, tx-byte, ...}}."""
    result: dict[str, dict[str, str]] = {}
    current_name = ""
    current: dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if re.match(r"^\d+$", line):
            if current_name and current:
                result[current_name] = current
            current = {}
            continue
        if line.startswith("name="):
            if current_name and current:
                result[current_name] = current
            current_name = line.split("=", 1)[1].strip()
            current = {"name": current_name}
        elif "=" in line:
            key, _, val = line.partition("=")
            current[key.strip()] = val.strip()
    if current_name and current:
        result[current_name] = current
    return result
