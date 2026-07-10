"""Flask web dashboard — 4D Syslog Analyzer for MikroTik."""

from __future__ import annotations

import json
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO

import config
from log_parser import parse_log_line
from mikrotik_advanced import MikroTikConnection
from syslog_server import LogStore, SyslogServer, log_store
from traffic_analyzer import (
    analyze_user_traffic,
    build_flow_matrix,
    dhcp_timeline,
    dns_resolution_map,
)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = config.WEB_SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

_syslog_server: SyslogServer | None = None
_connected_router: str = config.MIKROTIK_HOST


def _ensure_syslog() -> SyslogServer:
    global _syslog_server
    if _syslog_server is None:
        _syslog_server = SyslogServer(log_store)
        _syslog_server.start()

        def on_event(event):
            socketio.emit("new_log", event.to_dict())

        log_store.subscribe(on_event)
    return _syslog_server


@app.route("/")
def index():
    return render_template(
        "index.html",
        default_host=config.MIKROTIK_HOST,
        web_port=config.WEB_PORT,
    )


@app.route("/api/status")
def api_status():
    srv = _ensure_syslog()
    conn = MikroTikConnection(host=_connected_router)
    return jsonify(
        {
            "syslog_port": srv.port,
            "log_count": len(log_store.get_events()),
            "router_ip": _connected_router,
            "router_reachable": conn.ping(),
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/api/connect", methods=["POST"])
def api_connect():
    global _connected_router
    data = request.get_json(silent=True) or {}
    host = data.get("host", config.MIKROTIK_HOST)
    user = data.get("user", config.MIKROTIK_USER)
    password = data.get("password", config.MIKROTIK_PASSWORD)

    conn = MikroTikConnection(host=host, user=user, password=password)
    try:
        conn.connect()
        identity = conn.get_identity()
        _connected_router = host

        # Pull existing logs from router
        raw_logs = conn.fetch_logs(count=1000)
        for line in raw_logs:
            log_store.add_raw(line, source=host)

        # Optionally configure remote syslog to this collector
        collector_ip = data.get("collector_ip", "172.17.0.1")
        if data.get("setup_syslog", False):
            conn.configure_remote_syslog(collector_ip, config.SYSLOG_PORT)

        conn.disconnect()
        return jsonify(
            {
                "ok": True,
                "host": host,
                "identity": identity,
                "imported_logs": len(raw_logs),
            }
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/logs")
def api_logs():
    limit = request.args.get("limit", 200, type=int)
    service = request.args.get("service")
    search = request.args.get("q")
    events = log_store.get_events(limit=limit, service=service, search=search)
    return jsonify([e.to_dict() for e in reversed(events)])


@app.route("/api/stats")
def api_stats():
    return jsonify(log_store.get_stats())


@app.route("/api/analyzer/4d")
def api_4d_analyzer():
    events = log_store.get_events(limit=5000)
    return jsonify(
        {
            "flow_matrix": build_flow_matrix(events),
            "dhcp_timeline": dhcp_timeline(events),
            "dns_map": dns_resolution_map(events),
            "traffic": analyze_user_traffic(events),
        }
    )


@app.route("/api/dhcp")
def api_dhcp():
    events = log_store.get_events(limit=5000, service="dhcp")
    return jsonify(dhcp_timeline(events))


@app.route("/api/dns")
def api_dns():
    events = log_store.get_events(limit=5000, service="dns")
    return jsonify(dns_resolution_map(events))


@app.route("/api/router/live", methods=["POST"])
def api_router_live():
    data = request.get_json(silent=True) or {}
    host = data.get("host", _connected_router)
    conn = MikroTikConnection(host=host)
    try:
        conn.connect()
        result = {
            "leases": conn.fetch_dhcp_leases(),
            "dns_cache": conn.fetch_dns_cache(),
            "connections": conn.fetch_connections()[:50],
        }
        conn.disconnect()
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/export")
def api_export():
    path = log_store.save_snapshot()
    return jsonify({"path": str(path), "count": len(log_store.get_events())})


def run_dashboard(host: str | None = None, port: int | None = None) -> None:
    _ensure_syslog()
    socketio.run(
        app,
        host=host or config.WEB_HOST,
        port=port or config.WEB_PORT,
        debug=False,
        allow_unsafe_werkzeug=True,
    )


if __name__ == "__main__":
    run_dashboard()
