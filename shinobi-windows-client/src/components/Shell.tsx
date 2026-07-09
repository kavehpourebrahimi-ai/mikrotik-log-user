import { useEffect, useState } from "react";
import { ShinobiSocket } from "../lib/shinobi/socket";
import { paginateMonitors, useMonitorStore } from "../store/monitors";
import { useSessionStore } from "../store/session";
import { LiveGrid } from "./LiveGrid";

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
  const pageSize = useMonitorStore((state) => state.pageSize);
  const page = useMonitorStore((state) => state.page);
  const selectedMonitorId = useMonitorStore((state) => state.selectedMonitorId);

  const [activeTab, setActiveTab] = useState<"live" | "playback" | "users">(
    "live",
  );
  const [socketConnected, setSocketConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<string>("Waiting for events...");

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
        if (!cancelled) {
          setError(error.message);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    socket.connect(session, (event) => {
      setSocketConnected(true);
      if (event.f) {
        setLastEvent(`${event.f} @ ${new Date().toLocaleTimeString()}`);
      }
    });

    return () => {
      cancelled = true;
      socket.disconnect();
      setSocketConnected(false);
    };
  }, [client, session, setError, setLoading, setMonitors]);

  const selectedMonitor = monitors.find(
    (monitor) => monitor.mid === selectedMonitorId,
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <p className="eyebrow">Connected</p>
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
            Live
          </button>
          <button
            type="button"
            className={activeTab === "playback" ? "active" : ""}
            onClick={() => setActiveTab("playback")}
          >
            Playback
          </button>
          <button
            type="button"
            className={activeTab === "users" ? "active" : ""}
            onClick={() => setActiveTab("users")}
          >
            Users
          </button>
        </nav>

        <div className="sidebar-controls">
          <label>
            Grid density
            <select
              value={gridSize}
              onChange={(event) =>
                setGridSize(Number(event.target.value) as 4 | 6 | 8 | 10 | 16)
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
          <p className="status-line">{lastEvent}</p>
        </div>

        <button type="button" className="logout-button" onClick={logout}>
          Disconnect
        </button>
      </aside>

      <main className="workspace">
        {activeTab === "live" ? <LiveGrid /> : null}

        {activeTab === "playback" ? (
          <section className="panel">
            <header className="panel-header">
              <div>
                <h2>Playback</h2>
                <p>
                  Recording list and timeline playback will attach to the
                  selected camera through Shinobi&apos;s video APIs.
                </p>
              </div>
            </header>
            <div className="placeholder-card">
              {selectedMonitor ? (
                <>
                  <strong>{selectedMonitor.name}</strong>
                  <p>Monitor ID: {selectedMonitor.mid}</p>
                  <p>
                    Next step: load recordings from
                    <code> /videos/{session?.groupKey}/{selectedMonitor.mid}</code>
                  </p>
                </>
              ) : (
                <p>Select a camera from Live View to prepare playback.</p>
              )}
            </div>
          </section>
        ) : null}

        {activeTab === "users" ? (
          <section className="panel">
            <header className="panel-header">
              <div>
                <h2>Users</h2>
                <p>
                  Operator and sub-account management will use Shinobi register
                  and admin APIs with role-aware permissions.
                </p>
              </div>
            </header>
            <div className="placeholder-card">
              <p>Current operator: {session?.mail}</p>
              <p>Group key: {session?.groupKey}</p>
              <p>
                Next step: expose sub-account CRUD through
                <code> /register/{session?.groupKey}/...</code>
              </p>
            </div>
          </section>
        ) : null}

        <footer className="workspace-footer">
          <span>
            Page {page + 1} · {paginateMonitors(monitors, page, pageSize).length}{" "}
            visible streams · {monitors.length} total cameras
          </span>
        </footer>
      </main>
    </div>
  );
}
