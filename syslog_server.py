"""In-memory syslog store with UDP receiver for MikroTik logs."""

from __future__ import annotations

import json
import socket
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Callable

from log_parser import LogEvent, aggregate_events, parse_log_line

import config


class LogStore:
    """Thread-safe circular buffer of parsed log events."""

    def __init__(self, max_size: int | None = None):
        self.max_size = max_size or config.SYSLOG_MAX_LOGS
        self._events: deque[LogEvent] = deque(maxlen=self.max_size)
        self._lock = threading.Lock()
        self._listeners: list[Callable[[LogEvent], None]] = []

    def add_raw(self, raw: str, source: str = "") -> LogEvent:
        ts = datetime.now().strftime("%b/%d/%Y %H:%M:%S")
        if source:
            raw = f"[{source}] {raw}"
        event = parse_log_line(raw, default_ts=ts)
        with self._lock:
            self._events.append(event)
        for listener in self._listeners:
            try:
                listener(event)
            except Exception:
                pass
        return event

    def add_event(self, event: LogEvent) -> None:
        with self._lock:
            self._events.append(event)

    def get_events(
        self,
        limit: int | None = None,
        service: str | None = None,
        search: str | None = None,
    ) -> list[LogEvent]:
        with self._lock:
            events = list(self._events)
        if service:
            events = [e for e in events if e.service == service]
        if search:
            q = search.lower()
            events = [
                e
                for e in events
                if q in e.message.lower()
                or q in e.raw.lower()
                or q in e.dns_query.lower()
                or q in e.source_ip
            ]
        if limit:
            events = events[-limit:]
        return events

    def get_stats(self) -> dict:
        with self._lock:
            events = list(self._events)
        return aggregate_events(events)

    def subscribe(self, callback: Callable[[LogEvent], None]) -> None:
        self._listeners.append(callback)

    def save_snapshot(self, path: Path | None = None) -> Path:
        path = path or config.LOGS_DIR / f"snapshot_{datetime.now():%Y%m%d_%H%M%S}.json"
        with self._lock:
            data = [e.to_dict() for e in self._events]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def load_from_file(self, path: Path) -> int:
        if not path.exists():
            return 0
        data = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for item in data:
            self.add_event(LogEvent(**item))
            count += 1
        return count

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


class SyslogServer:
    """UDP syslog listener (RFC 3164-ish)."""

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
            # Port 514 may need root; fall back to 5514
            self.port = 5514
            self._sock.bind((self.host, self.port))
        self._sock.settimeout(1.0)
        while not self._stop.is_set():
            try:
                data, addr = self._sock.recvfrom(65535)
                message = data.decode("utf-8", errors="replace").strip()
                # Strip syslog PRI header if present: <134>...
                if message.startswith("<") and ">" in message:
                    message = message.split(">", 1)[1].strip()
                self.store.add_raw(message, source=addr[0])
            except socket.timeout:
                continue
            except OSError:
                break


# Global singleton used by web dashboard and CLI
log_store = LogStore()
