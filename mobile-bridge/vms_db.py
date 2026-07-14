"""Read the camera / device list from the VMS MySQL database.

The bridge never asks the operator to re-enter camera credentials: it reads the
camera list (and the per-device IP / port / user / password) straight from the
`surveillancesystem` database that the Windows VMS server already maintains.

Relevant tables (reverse engineered):

    channel(Channel_Guid, Device_Guid, Name, ChannelType, Id)
    device(Device_Guid, ParentGuid, Mac, ?, PrivateAddress, PublicAddress,
           Port, ChannelCount, ..., User, Password, ...)
    channelproperty(Channel_Guid, Hidden, Disabled, Preview, ...)

Only the columns we actually need are selected, addressed by name so the code is
resilient to unknown/extra columns.
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    import pymysql
except ImportError:  # pragma: no cover - dependency is documented in requirements
    pymysql = None


@dataclass
class Camera:
    guid: str
    name: str
    device_guid: str
    ip: str
    port: int
    user: str
    password: str
    channel_no: int
    disabled: bool


class VmsDatabase:
    def __init__(self, host: str, port: int, user: str, password: str, db: str):
        self._cfg = dict(host=host, port=port, user=user, password=password, db=db)

    def _connect(self):
        if pymysql is None:
            raise RuntimeError(
                "pymysql is not installed. Run: pip install -r requirements.txt"
            )
        return pymysql.connect(
            host=self._cfg["host"],
            port=self._cfg["port"],
            user=self._cfg["user"],
            password=self._cfg["password"],
            database=self._cfg["db"],
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
            read_timeout=10,
        )

    def list_cameras(self) -> list[Camera]:
        """Return every enabled video channel with its device connection info."""

        sql = """
            SELECT c.Channel_Guid  AS guid,
                   c.Name          AS name,
                   c.Device_Guid   AS device_guid,
                   d.PrivateAddress AS ip,
                   d.Port          AS port,
                   d.User          AS user,
                   d.Password      AS password,
                   d.DeviceIndex   AS device_index,
                   cp.Disabled     AS disabled,
                   cp.DeviceIndex  AS channel_no
            FROM channel c
            JOIN device d          ON c.Device_Guid = d.Device_Guid
            LEFT JOIN channelproperty cp ON cp.Channel_Guid = c.Channel_Guid
            WHERE c.ChannelType = '2001'   -- video channels only
        """
        cams: list[Camera] = []
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                for row in cur.fetchall():
                    cams.append(self._row_to_camera(row))
        cams.sort(key=lambda c: (c.name or c.guid))
        return cams

    @staticmethod
    def _row_to_camera(row: dict) -> Camera:
        def _int(v, default=0):
            try:
                return int(str(v).strip())
            except (TypeError, ValueError):
                return default

        return Camera(
            guid=row.get("guid", ""),
            name=(row.get("name") or "").strip() or row.get("guid", ""),
            device_guid=row.get("device_guid", ""),
            ip=(row.get("ip") or "").strip(),
            port=_int(row.get("port"), 554),
            user=(row.get("user") or "admin").strip(),
            password=(row.get("password") or "").strip(),
            channel_no=_int(row.get("channel_no"), 0) + 1,
            disabled=bool(_int(row.get("disabled"), 0)),
        )
