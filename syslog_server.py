"""In-memory + SQLite syslog store with UDP receiver."""

from __future__ import annotations

import json
import socket
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Callable

from log_database import log_db
from log_parser import LogEvent, aggregate_events, parse_log_line

import config


class LogStore:
    """Thread-safe buffer + persistent SQLite stack."""

    def __init__(self, max_size: int | None = None):
        self.max_size = max_size or config.SYSLOG_MAX_LOGS
        self._events: deque[LogEvent] = deque(maxlen=self.max_size)
        self._lock = threading.Lock()
        self._listeners: list[Callable[[LogEvent], None]] = []
        self._router_ip: str = config.MIKROTIK_HOST

    def set_router_ip(self, ip: str) -> None:
        self._router_ip = ip

    def add_raw(self, raw: str, source: str = "") -> LogEvent:
        ts = datetime.now().strftime("%b/%d/%Y %H:%M:%S")
        router = source or self._router_ip
        if source:
            raw = f"[{source}] {raw}"
        event = parse_log_line(raw, default_ts=ts)
        with self._lock:
            self._events.append(event)
        log_db.insert_event(event, router_ip=router)
        for listener in self._listeners:
            try:
                listener(event)
            except Exception:
                pass
        return event

    def add_event(self, event: LogEvent, router_ip: str = "") -> None:
        with self._lock:
            self._events.append(event)
        log_db.insert_event(event, router_ip=router_ip or self._router_ip)

    def get_events(
        self,
        limit: int | None = None,
        offset: int = 0,
        service: str | None = None,
        search: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        source_ip: str | None = None,
        dest_ip: str | None = None,
        username: str | None = None,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
        use_db: bool = True,
    ) -> list[LogEvent]:
        if use_db and log_db.total_count() > 0:
            rows = log_db.query_events(
                limit=limit or 500,
                offset=offset,
                service=service,
                search=search,
                date_from=date_from,
                date_to=date_to,
                source_ip=source_ip,
                dest_ip=dest_ip,
                username=username,
                sort_by="id" if sort_by == "timestamp" else sort_by,
                sort_order=sort_order,
            )
            return [_row_to_event(r) for r in rows]

        from traffic_analyzer import filter_events, sort_events

        with self._lock:
            events = list(self._events)
        events = filter_events(
            events, service=service, search=search, date_from=date_from,
            date_to=date_to, source_ip=source_ip, dest_ip=dest_ip, username=username,
        )
        events = sort_events(events, sort_by=sort_by, order=sort_order)
        if limit:
            events = events[:limit]
        return events

    def get_stats(self) -> dict:
        if log_db.total_count() > 0:
            by_service = log_db.stats_by_service()
            with self._lock:
                mem = list(self._events)
            agg = aggregate_events(mem[-5000:]) if mem else {}
            agg["total"] = log_db.total_count()
            agg["by_service"] = by_service
            return agg
        with self._lock:
            events = list(self._events)
        return aggregate_events(events)

    def subscribe(self, callback: Callable[[LogEvent], None]) -> None:
        self._listeners.append(callback)

    def save_snapshot(self, path: Path | None = None) -> Path:
        path = path or config.LOGS_DIR / f"snapshot_{datetime.now():%Y%m%d_%H%M%S}.json"
        rows = log_db.query_events(limit=999999, sort_by="id", sort_order="ASC")
        path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


def _row_to_event(row: dict) -> LogEvent:
    return LogEvent(
        timestamp=row.get("timestamp", ""),
        topic=row.get("topic", ""),
        message=row.get("message", ""),
        source_ip=row.get("source_ip", ""),
        dest_ip=row.get("dest_ip", ""),
        protocol=row.get("protocol", ""),
        service=row.get("service", ""),
        client_mac=row.get("client_mac", ""),
        hostname=row.get("hostname", ""),
        dns_query=row.get("dns_query", ""),
        dhcp_action=row.get("dhcp_action", ""),
        interface=row.get("interface", ""),
        username=row.get("username", ""),
        vpn_type=row.get("vpn_type", ""),
        action=row.get("action", ""),
        dest_name=row.get("dest_name", ""),
        login_from_ip=row.get("login_from_ip", ""),
        raw=row.get("raw", ""),
    )


class SyslogServer:
    """UDP syslog listener."""

    def __init__(self, store: LogStore, host: str | None = None, port: int | None = None):
        self.store = store
        self.host = host or config.SYSLOG_HOST
        self.port = port or config.SYSLOG_PORT
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._sock: socket.socket | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="syslog-udp")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    def _run(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._sock.bind((self.host, self.port))
        except OSError:
            self.port = 5514
            self._sock.bind((self.host, self.port))
        self._sock.settimeout(1.0)
        while not self._stop.is_set():
            try:
                data, addr = self._sock.recvfrom(65535)
                message = data.decode("utf-8", errors="replace").strip()
                if message.startswith("<") and ">" in message:
                    message = message.split(">", 1)[1].strip()
                self.store.add_raw(message, source=addr[0])
            except socket.timeout:
                continue
            except OSError:
                break


log_store = LogStore()
