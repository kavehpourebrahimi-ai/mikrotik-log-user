"""Flask web dashboard — FortiAnalyzer-style MikroTik log analyzer."""

from __future__ import annotations

from datetime import datetime

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO

import config
from log_database import log_db
from mikrotik_advanced import MikroTikConnection
from ppp_analytics import build_ppp_report, fetch_and_store_hotspot_sessions, fetch_and_store_ppp_sessions
from router_sync import router_sync
from syslog_server import SyslogServer, log_store
from traffic_analyzer import (
    analyze_user_traffic,
    build_flow_matrix,
    dhcp_timeline,
    dns_resolution_map,
    hotspot_activity,
    login_audit,
)
from tunnel_analytics import build_tunnel_report, fetch_and_store_tunnels
from user_analytics import build_users_report, user_detail

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
        router_sync.start()

        def on_event(event):
            socketio.emit("new_log", event.to_dict())

        log_store.subscribe(on_event)
    return _syslog_server


def _query_params():
    return {
        "limit": request.args.get("limit", 500, type=int),
        "offset": request.args.get("offset", 0, type=int),
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


def _get_events(**extra):
    params = _query_params()
    params.update(extra)
    return log_store.get_events(**params)


@app.route("/")
def index():
    return render_template("index.html", default_host=config.MIKROTIK_HOST, web_port=config.WEB_PORT)


@app.route("/api/status")
def api_status():
    srv = _ensure_syslog()
    conn = MikroTikConnection(host=_connected_router)
    return jsonify({
        "syslog_port": srv.port,
        "log_count": log_db.total_count(),
        "router_ip": _connected_router,
        "router_reachable": conn.ping(),
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/connect", methods=["POST"])
def api_connect():
    global _connected_router
    data = request.get_json(silent=True) or {}
    host = data.get("host", config.MIKROTIK_HOST)
    user = data.get("user", config.MIKROTIK_USER)
    password = data.get("password", config.MIKROTIK_PASSWORD)

    peer_host = data.get("peer_host", config.MIKROTIK_PEER_HOST)

    conn = MikroTikConnection(host=host, user=user, password=password)
    try:
        conn.connect()
        identity = conn.get_identity()
        _connected_router = host
        log_store.set_router_ip(host)
        router_sync.configure(host, user, password, peer_host=peer_host)

        raw_logs = conn.fetch_logs(count=3000)
        for line in raw_logs:
            log_store.add_raw(line, source=host)

        fetch_and_store_ppp_sessions(conn)
        fetch_and_store_hotspot_sessions(conn)
        tunnels = fetch_and_store_tunnels(conn)

        # MikroTik peer (second router in IPIP link)
        if peer_host:
            peer = MikroTikConnection(host=peer_host, user=user, password=password)
            try:
                peer.connect()
                for line in peer.fetch_logs(count=2000):
                    log_store.add_raw(line, source=peer_host)
                fetch_and_store_tunnels(peer)
                if data.get("setup_syslog", False):
                    collector_ip = data.get("collector_ip", request.host.split(":")[0])
                    peer.configure_remote_syslog(collector_ip, config.SYSLOG_PORT)
                peer.disconnect()
            except Exception:
                pass

        collector_ip = data.get("collector_ip", request.host.split(":")[0])
        if data.get("setup_syslog", False):
            conn.configure_remote_syslog(collector_ip, config.SYSLOG_PORT)

        conn.disconnect()
        router_sync.sync_now()

        script = MikroTikConnection.syslog_setup_script(collector_ip, config.SYSLOG_PORT)
        return jsonify({
            "ok": True, "host": host, "peer_host": peer_host, "identity": identity,
            "imported_logs": len(raw_logs), "tunnels": len(tunnels), "syslog_script": script,
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/logs")
def api_logs():
    events = _get_events()
    return jsonify([e.to_dict() for e in events])


@app.route("/api/stats")
def api_stats():
    return jsonify(log_store.get_stats())


@app.route("/api/users")
def api_users():
    params = _query_params()
    return jsonify(build_users_report(
        search=params["search"], date_from=params["date_from"],
        date_to=params["date_to"], limit=params["limit"],
    ))


@app.route("/api/users/<username>")
def api_user_detail(username):
    return jsonify(user_detail(username, limit=_query_params()["limit"]))


@app.route("/api/ppp")
def api_ppp():
    params = _query_params()
    report = build_ppp_report(date_from=params["date_from"], date_to=params["date_to"])
    report["sync"] = router_sync.sync_now()
    return jsonify(report)


@app.route("/api/tunnels")
def api_tunnels():
    params = _query_params()
    return jsonify(build_tunnel_report(date_from=params["date_from"], date_to=params["date_to"]))


@app.route("/api/analyzer/4d")
def api_4d():
    events = _get_events(limit=10000)
    return jsonify({
        "flow_matrix": build_flow_matrix(events),
        "dhcp_timeline": dhcp_timeline(events),
        "dns_map": dns_resolution_map(events),
        "traffic": analyze_user_traffic(events),
    })


@app.route("/api/hotspot")
def api_hotspot():
    params = _query_params()
    events = log_store.get_events(service="hotspot", limit=99999,
                                  date_from=params["date_from"], date_to=params["date_to"])
    live = log_db.latest_hotspot_snapshot(_connected_router)
    return jsonify({**hotspot_activity(events), "live_sessions": live})


@app.route("/api/login-audit")
def api_login_audit():
    events = _get_events(limit=50000)
    return jsonify(login_audit(events))


@app.route("/api/dhcp")
def api_dhcp():
    return jsonify(dhcp_timeline(_get_events(service="dhcp", limit=99999)))


@app.route("/api/dns")
def api_dns():
    return jsonify(dns_resolution_map(_get_events(service="dns", limit=99999)))


@app.route("/api/sync", methods=["POST"])
def api_sync():
    return jsonify(router_sync.sync_now())


@app.route("/api/mikrotik/syslog-script")
def api_syslog_script():
    remote_ip = request.args.get("server_ip", request.host.split(":")[0])
    port = request.args.get("port", config.SYSLOG_PORT, type=int)
    return jsonify({"script": MikroTikConnection.syslog_setup_script(remote_ip, port)})


@app.route("/api/export")
def api_export():
    path = log_store.save_snapshot()
    return jsonify({"path": str(path), "count": log_db.total_count()})


def run_dashboard(host=None, port=None):
    _ensure_syslog()
    socketio.run(app, host=host or config.WEB_HOST, port=port or config.WEB_PORT,
                 debug=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    run_dashboard()
