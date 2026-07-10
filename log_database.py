"""Persistent SQLite log storage — FortiAnalyzer-style log stack."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import config
from log_parser import LogEvent

DB_PATH = config.DATA_DIR / "logs.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS log_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at TEXT NOT NULL,
    timestamp TEXT,
    topic TEXT,
    message TEXT,
    source_ip TEXT,
    dest_ip TEXT,
    protocol TEXT,
    service TEXT,
    client_mac TEXT,
    hostname TEXT,
    dns_query TEXT,
    dhcp_action TEXT,
    interface TEXT,
    username TEXT,
    vpn_type TEXT,
    action TEXT,
    dest_name TEXT,
    login_from_ip TEXT,
    raw TEXT,
    router_ip TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_ts ON log_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_service ON log_events(service);
CREATE INDEX IF NOT EXISTS idx_username ON log_events(username);
CREATE INDEX IF NOT EXISTS idx_source ON log_events(source_ip);
CREATE INDEX IF NOT EXISTS idx_received ON log_events(received_at);

CREATE TABLE IF NOT EXISTS ppp_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    router_ip TEXT,
    data_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hotspot_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    router_ip TEXT,
    data_json TEXT NOT NULL
);
"""


class LogDatabase:
    """Thread-safe SQLite backend for syslog stack."""

    def __init__(self, path: Path | None = None):
        self.path = path or DB_PATH
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def insert_event(self, event: LogEvent, router_ip: str = "") -> int:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO log_events (
                    received_at, timestamp, topic, message, source_ip, dest_ip,
                    protocol, service, client_mac, hostname, dns_query, dhcp_action,
                    interface, username, vpn_type, action, dest_name, login_from_ip,
                    raw, router_ip
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    datetime.now().isoformat(),
                    event.timestamp,
                    event.topic,
                    event.message,
                    event.source_ip,
                    event.dest_ip,
                    event.protocol,
                    event.service,
                    event.client_mac,
                    event.hostname,
                    event.dns_query,
                    event.dhcp_action,
                    event.interface,
                    event.username,
                    event.vpn_type,
                    event.action,
                    event.dest_name,
                    event.login_from_ip,
                    event.raw,
                    router_ip,
                ),
            )
            return cur.lastrowid or 0

    def query_events(
        self,
        limit: int = 500,
        offset: int = 0,
        service: str | None = None,
        search: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        source_ip: str | None = None,
        dest_ip: str | None = None,
        username: str | None = None,
        sort_by: str = "id",
        sort_order: str = "DESC",
    ) -> list[dict[str, Any]]:
        allowed_sort = {
            "id", "timestamp", "service", "source_ip", "dest_ip", "username", "received_at"
        }
        col = sort_by if sort_by in allowed_sort else "id"
        order = "ASC" if sort_order.upper() == "ASC" else "DESC"

        clauses: list[str] = []
        params: list[Any] = []

        if service:
            clauses.append("service = ?")
            params.append(service)
        if search:
            clauses.append(
                "(message LIKE ? OR raw LIKE ? OR dns_query LIKE ? OR username LIKE ?)"
            )
            q = f"%{search}%"
            params.extend([q, q, q, q])
        if source_ip:
            clauses.append("(source_ip LIKE ? OR login_from_ip LIKE ?)")
            params.extend([f"%{source_ip}%", f"%{source_ip}%"])
        if dest_ip:
            clauses.append("(dest_ip LIKE ? OR dest_name LIKE ? OR dns_query LIKE ?)")
            params.extend([f"%{dest_ip}%", f"%{dest_ip}%", f"%{dest_ip}%"])
        if username:
            clauses.append("username LIKE ?")
            params.append(f"%{username}%")
        if date_from:
            clauses.append("received_at >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("received_at <= ?")
            params.append(date_to)

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM log_events{where} ORDER BY {col} {order} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._lock, self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def count_events(self, **filters) -> int:
        rows = self.query_events(limit=999999999, **filters)
        return len(rows)

    def stats_by_service(self) -> dict[str, int]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT service, COUNT(*) as cnt FROM log_events GROUP BY service ORDER BY cnt DESC"
            ).fetchall()
        return {r["service"] or "unknown": r["cnt"] for r in rows}

    def total_count(self) -> int:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) as c FROM log_events").fetchone()
        return row["c"] if row else 0

    def save_ppp_snapshot(self, router_ip: str, sessions: list[dict]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO ppp_snapshots (captured_at, router_ip, data_json) VALUES (?,?,?)",
                (datetime.now().isoformat(), router_ip, json.dumps(sessions, ensure_ascii=False)),
            )

    def latest_ppp_snapshot(self, router_ip: str = "") -> list[dict]:
        with self._lock, self._connect() as conn:
            if router_ip:
                row = conn.execute(
                    "SELECT data_json FROM ppp_snapshots WHERE router_ip=? ORDER BY id DESC LIMIT 1",
                    (router_ip,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT data_json FROM ppp_snapshots ORDER BY id DESC LIMIT 1"
                ).fetchone()
        return json.loads(row["data_json"]) if row else []

    def save_hotspot_snapshot(self, router_ip: str, sessions: list[dict]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO hotspot_snapshots (captured_at, router_ip, data_json) VALUES (?,?,?)",
                (datetime.now().isoformat(), router_ip, json.dumps(sessions, ensure_ascii=False)),
            )

    def latest_hotspot_snapshot(self, router_ip: str = "") -> list[dict]:
        with self._lock, self._connect() as conn:
            if router_ip:
                row = conn.execute(
                    "SELECT data_json FROM hotspot_snapshots WHERE router_ip=? ORDER BY id DESC LIMIT 1",
                    (router_ip,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT data_json FROM hotspot_snapshots ORDER BY id DESC LIMIT 1"
                ).fetchone()
        return json.loads(row["data_json"]) if row else []


log_db = LogDatabase()
