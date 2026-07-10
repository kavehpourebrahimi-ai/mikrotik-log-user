"""Background sync — poll MikroTik for live PPP/Hotspot session data."""

from __future__ import annotations

import threading
import time

import config
from mikrotik_advanced import MikroTikConnection
from ppp_analytics import fetch_and_store_hotspot_sessions, fetch_and_store_ppp_sessions


class RouterSyncWorker:
    """Periodically fetch live session data from MikroTik."""

    def __init__(self, interval: int = 60):
        self.interval = interval
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._host = config.MIKROTIK_HOST
        self._user = config.MIKROTIK_USER
        self._password = config.MIKROTIK_PASSWORD

    def configure(self, host: str, user: str, password: str) -> None:
        self._host = host
        self._user = user
        self._password = password

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="router-sync")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def sync_now(self) -> dict:
        conn = MikroTikConnection(host=self._host, user=self._user, password=self._password)
        try:
            conn.connect()
            ppp = fetch_and_store_ppp_sessions(conn)
            hs = fetch_and_store_hotspot_sessions(conn)
            conn.disconnect()
            return {"ppp": len(ppp), "hotspot": len(hs), "ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.sync_now()
            self._stop.wait(self.interval)


router_sync = RouterSyncWorker()
