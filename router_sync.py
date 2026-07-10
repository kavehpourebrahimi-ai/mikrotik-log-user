"""Background sync — poll MikroTik for live PPP/Hotspot session data."""

from __future__ import annotations

import threading
import time

import config
from mikrotik_advanced import MikroTikConnection
from ppp_analytics import fetch_and_store_hotspot_sessions, fetch_and_store_ppp_sessions
from tunnel_analytics import fetch_and_store_tunnels


class RouterSyncWorker:
    """Periodically fetch live session data from MikroTik."""

    def __init__(self, interval: int = 60):
        self.interval = interval
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._host = config.MIKROTIK_HOST
        self._user = config.MIKROTIK_USER
        self._password = config.MIKROTIK_PASSWORD
        self._peer_host = getattr(config, "MIKROTIK_PEER_HOST", "") or ""
        self._peer_user = config.MIKROTIK_USER
        self._peer_password = config.MIKROTIK_PASSWORD

    def configure(self, host: str, user: str, password: str, peer_host: str = "") -> None:
        self._host = host
        self._user = user
        self._password = password
        if peer_host:
            self._peer_host = peer_host

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="router-sync")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def sync_now(self) -> dict:
        result = {"ok": True, "routers": []}
        for label, host, user, pwd in (
            ("primary", self._host, self._user, self._password),
            ("peer", self._peer_host, self._peer_user, self._peer_password),
        ):
            if not host:
                continue
            conn = MikroTikConnection(host=host, user=user, password=pwd)
            try:
                conn.connect()
                ppp = fetch_and_store_ppp_sessions(conn)
                hs = fetch_and_store_hotspot_sessions(conn)
                tunnels = fetch_and_store_tunnels(conn)
                conn.disconnect()
                result["routers"].append({
                    "label": label, "host": host,
                    "ppp": len(ppp), "hotspot": len(hs), "tunnels": len(tunnels),
                })
            except Exception as exc:
                result["routers"].append({"label": label, "host": host, "error": str(exc)})
                result["ok"] = False
        return result

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.sync_now()
            self._stop.wait(self.interval)


router_sync = RouterSyncWorker()
