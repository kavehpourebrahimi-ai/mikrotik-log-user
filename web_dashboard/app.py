"""Flask web dashboard — 4D Syslog Analyzer for MikroTik."""

from __future__ import annotations

from datetime import datetime

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO

import config
from mikrotik_advanced import MikroTikConnection
from syslog_server import SyslogServer, log_store
from traffic_analyzer import (
    analyze_user_traffic,
    build_flow_matrix,
    dhcp_timeline,
    dns_resolution_map,
    hotspot_activity,
    login_audit,
    vpn_summary,
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


def _query_params():
    return {
        "limit": request.args.get("limit", 500, type=int),
        "service": request.args.get("service") or None,
        "search": request.args.get("q") or None,
        "date_from": request.args.get("date_from") or None,
        "date_to": request.args.get("date_to") or None,
        "source_ip": request.args.get("source_ip") or None,
        "dest_ip": request.args.get("dest_ip") or None,
        "username": request.args.get("username") or None,
        "sort_by": request.args.get("sort_by", "timestamp"),
        "sort_order": request.args.get("sort_order", "desc"),
    }


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
            "log_count": len(log_store.get_events(limit=999999)),
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

        raw_logs = conn.fetch_logs(count=2000)
        for line in raw_logs:
            log_store.add_raw(line, source=host)

        collector_ip = data.get("collector_ip", request.host.split(":")[0])
        if data.get("setup_syslog", False):
            conn.configure_remote_syslog(collector_ip, config.SYSLOG_PORT)

        conn.disconnect()
        return jsonify(
            {
                "ok": True,
                "host": host,
                "identity": identity,
                "imported_logs": len(raw_logs),
                "syslog_script": MikroTikConnection.syslog_setup_script(collector_ip, config.SYSLOG_PORT),
            }
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/logs")
def api_logs():
    params = _query_params()
    events = log_store.get_events(**params)
    return jsonify([e.to_dict() for e in events])


@app.route("/api/stats")
def api_stats():
    params = _query_params()
    del params["sort_by"]
    del params["sort_order"]
    events = log_store.get_events(**params, limit=999999)
    from log_parser import aggregate_events

    return jsonify(aggregate_events(events))


@app.route("/api/analyzer/4d")
def api_4d_analyzer():
    params = _query_params()
    del params["sort_by"]
    del params["sort_order"]
    events = log_store.get_events(**params, limit=999999)
    return jsonify(
        {
            "flow_matrix": build_flow_matrix(events),
            "dhcp_timeline": dhcp_timeline(events),
            "dns_map": dns_resolution_map(events),
            "traffic": analyze_user_traffic(events),
        }
    )


@app.route("/api/vpn")
def api_vpn():
    params = _query_params()
    del params["sort_by"]
    del params["sort_order"]
    params["service"] = "vpn"
    events = log_store.get_events(**params, limit=999999)
    return jsonify(vpn_summary(events))


@app.route("/api/hotspot")
def api_hotspot():
    params = _query_params()
    del params["sort_by"]
    del params["sort_order"]
    params["service"] = "hotspot"
    events = log_store.get_events(**params, limit=999999)
    return jsonify(hotspot_activity(events))


@app.route("/api/login-audit")
def api_login_audit():
    params = _query_params()
    del params["sort_by"]
    del params["sort_order"]
    events = log_store.get_events(**params, limit=999999)
    return jsonify(login_audit(events))


@app.route("/api/dhcp")
def api_dhcp():
    params = _query_params()
    del params["sort_by"]
    del params["sort_order"]
    params["service"] = "dhcp"
    events = log_store.get_events(**params, limit=999999)
    return jsonify(dhcp_timeline(events))


@app.route("/api/dns")
def api_dns():
    params = _query_params()
    del params["sort_by"]
    del params["sort_order"]
    params["service"] = "dns"
    events = log_store.get_events(**params, limit=999999)
    return jsonify(dns_resolution_map(events))


@app.route("/api/mikrotik/syslog-script")
def api_syslog_script():
    remote_ip = request.args.get("server_ip", request.host.split(":")[0])
    port = request.args.get("port", config.SYSLOG_PORT, type=int)
    return jsonify({"script": MikroTikConnection.syslog_setup_script(remote_ip, port)})


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
            "ppp_active": conn.fetch_ppp_active(),
            "hotspot_active": conn.fetch_hotspot_active(),
        }
        conn.disconnect()
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/export")
def api_export():
    path = log_store.save_snapshot()
    return jsonify({"path": str(path), "count": len(log_store.get_events(limit=999999))})


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
