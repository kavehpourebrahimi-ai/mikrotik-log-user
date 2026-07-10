"""User listing and lookup via MikroTik SSH."""

from __future__ import annotations

from typing import Any

from mikrotik_advanced import MikroTikConnection


def list_all_users(host: str | None = None) -> list[dict[str, Any]]:
    conn = MikroTikConnection(host=host)
    try:
        conn.connect()
        users = conn.fetch_users()
        return [_normalize_user(u) for u in users]
    finally:
        conn.disconnect()


def get_user_info(username: str, host: str | None = None) -> dict[str, Any] | None:
    users = list_all_users(host=host)
    for user in users:
        if user.get("name", "").lower() == username.lower():
            return user
    return None


def search_by_group(group: str, host: str | None = None) -> list[dict[str, Any]]:
    users = list_all_users(host=host)
    return [u for u in users if u.get("profile", "").lower() == group.lower()]


def _normalize_user(raw: dict[str, str]) -> dict[str, Any]:
    return {
        "name": raw.get("name", raw.get("user", "")),
        "profile": raw.get("profile", raw.get("group", "")),
        "disabled": raw.get("disabled", "false") == "true",
        "comment": raw.get("comment", ""),
        "address": raw.get("address", raw.get("remote-address", "")),
        "uptime": raw.get("uptime", ""),
        "raw": raw,
    }
