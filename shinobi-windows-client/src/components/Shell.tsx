import { useEffect, useMemo, useState } from "react";
import { ShinobiSocket } from "../lib/shinobi/socket";
import { mapSocketEventToAlarm, useAlarmStore } from "../store/alarms";
import { paginateMonitors, useMonitorStore } from "../store/monitors";
import { PERFORMANCE_PRESETS } from "../store/settings";
import { useSettingsStore } from "../store/settingsStore";
import { useSessionStore } from "../store/session";
import { AlarmFeed } from "./AlarmFeed";
import { FocusView } from "./FocusView";
import { LiveGrid } from "./LiveGrid";
import { PlaybackPanel } from "./PlaybackPanel";

const socket = new ShinobiSocket();

export function Shell() {
  const session = useSessionStore((state) => state.session);
  const client = useSessionStore((state) => state.client);
  const logout = useSessionStore((state) => state.logout);
  const monitors = useMonitorStore((state) => state.monitors);
  const setMonitors = useMonitorStore((state) => state.setMonitors);
  const setLoading = useMonitorStore((state) => state.setLoading);
  const setError = useMonitorStore((state) => state.setError);
  const gridSize = useMonitorStore((state) => state.gridSize);
  const setGridSize = useMonitorStore((state) => state.setGridSize);
  const page = useMonitorStore((state) => state.page);
  const selectedMonitorId = useMonitorStore((state) => state.selectedMonitorId);
  const setSelectedMonitorId = useMonitorStore(
    (state) => state.setSelectedMonitorId,
  );

  const performanceMode = useSettingsStore((state) => state.performanceMode);
  const setPerformanceMode = useSettingsStore(
    (state) => state.setPerformanceMode,
  );
  const snapshotIntervalMs = useSettingsStore(
    (state) => state.snapshotIntervalMs,
  );
  const setSnapshotIntervalMs = useSettingsStore(
    (state) => state.setSnapshotIntervalMs,
  );
  const pageSize = useSettingsStore((state) => state.pageSize);
  const setPageSize = useSettingsStore((state) => state.setPageSize);

  const pushAlarm = useAlarmStore((state) => state.pushAlarm);

  const [activeTab, setActiveTab] = useState<"live" | "playback">("live");
  const [socketConnected, setSocketConnected] = useState(false);

  useEffect(() => {
    if (!client || !session) return;

    let cancelled = false;
    setLoading(true);
    client
      .listMonitors()
      .then((items) => {
        if (!cancelled) {
          setMonitors(items);
          setError(null);
        }
      })
      .catch((error: Error) => {
        if (!cancelled) setError(error.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    socket.connect(session, (event) => {
      setSocketConnected(true);
      const monitor = useMonitorStore
        .getState()
        .monitors.find((entry) => entry.mid === String(event.mid));
      const alarm = mapSocketEventToAlarm(
        event as Record<string, unknown>,
        monitor?.name,
      );
      if (alarm) pushAlarm(alarm);
    });

    return () => {
      cancelled = true;
      socket.disconnect();
      setSocketConnected(false);
    };
  }, [client, session, setError, setLoading, setMonitors, pushAlarm]);

  const selectedMonitor = useMemo(
    () => monitors.find((monitor) => monitor.mid === selectedMonitorId) ?? null,
    [monitors, selectedMonitorId],
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <p className="eyebrow">Operator Desk</p>
          <h1>Shinobi Client</h1>
          <p>{session?.mail}</p>
          <small>{session?.serverUrl}</small>
        </div>

        <nav className="sidebar-nav">
          <button
            type="button"
            className={activeTab === "live" ? "active" : ""}
            onClick={() => setActiveTab("live")}
          >
            Live Control
          </button>
          <button
            type="button"
            className={activeTab === "playback" ? "active" : ""}
            onClick={() => setActiveTab("playback")}
          >
            Playback
          </button>
        </nav>

        <div className="sidebar-controls">
          <label>
            Performance mode
            <select
              value={performanceMode}
              onChange={(event) =>
                setPerformanceMode(
                  event.target.value as typeof performanceMode,
                )
              }
            >
              {Object.entries(PERFORMANCE_PRESETS).map(([key, preset]) => (
                <option key={key} value={key}>
                  {preset.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Snapshot refresh (ms)
            <input
              type="number"
              min={1000}
              step={500}
              value={snapshotIntervalMs}
              onChange={(event) =>
                setSnapshotIntervalMs(Number(event.target.value))
              }
            />
          </label>

          <label>
            Cameras per page
            <select
              value={pageSize}
              onChange={(event) => setPageSize(Number(event.target.value))}
            >
              <option value={8}>8</option>
              <option value={16}>16</option>
              <option value={32}>32</option>
              <option value={64}>64</option>
            </select>
          </label>

          <label>
            Grid density
            <select
              value={gridSize}
              onChange={(event) =>
                setGridSize(Number(event.target.value) as typeof gridSize)
              }
            >
              <option value={4}>2 x 2</option>
              <option value={6}>3 x 2</option>
              <option value={8}>4 x 2</option>
              <option value={10}>5 x 2</option>
              <option value={16}>4 x 4</option>
            </select>
          </label>

          <p className="status-line">
            Socket: {socketConnected ? "connected" : "connecting"}
          </p>
          <p className="status-line">Cameras: {monitors.length}</p>
        </div>

        <button type="button" className="logout-button" onClick={logout}>
          Disconnect
        </button>
      </aside>

      <main className="workspace">
        {activeTab === "live" ? (
          <div className="live-workspace">
            <LiveGrid />
            <div className="live-side-stack">
              <FocusView
                session={session!}
                monitor={selectedMonitor}
                onClose={() => setSelectedMonitorId(null)}
              />
              <AlarmFeed />
            </div>
          </div>
        ) : null}

        {activeTab === "playback" && client ? (
          <PlaybackPanel client={client} monitor={selectedMonitor} />
        ) : null}

        <footer className="workspace-footer">
          <span>
            Mode: {PERFORMANCE_PRESETS[performanceMode].label} · Page {page + 1}{" "}
            · {paginateMonitors(monitors, page, pageSize).length} visible ·{" "}
            {monitors.length} total cameras
          </span>
        </footer>
      </main>
    </div>
  );
}
