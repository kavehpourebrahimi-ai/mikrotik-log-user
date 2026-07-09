import { useMemo, useState } from "react";
import { paginateMonitors, useMonitorStore } from "../store/monitors";
import { useSettingsStore } from "../store/settingsStore";
import { useSessionStore } from "../store/session";
import { PERFORMANCE_PRESETS } from "../store/settings";
import { CameraTile } from "./CameraTile";

export function LiveGrid() {
  const session = useSessionStore((state) => state.session);
  const monitors = useMonitorStore((state) => state.monitors);
  const gridSize = useMonitorStore((state) => state.gridSize);
  const page = useMonitorStore((state) => state.page);
  const selectedMonitorId = useMonitorStore((state) => state.selectedMonitorId);
  const setSelectedMonitorId = useMonitorStore(
    (state) => state.setSelectedMonitorId,
  );
  const setPage = useMonitorStore((state) => state.setPage);
  const performanceMode = useSettingsStore((state) => state.performanceMode);
  const snapshotIntervalMs = useSettingsStore(
    (state) => state.snapshotIntervalMs,
  );
  const pageSize = useSettingsStore((state) => state.pageSize);

  const [search, setSearch] = useState("");

  const filteredMonitors = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return monitors;
    return monitors.filter(
      (monitor) =>
        monitor.name.toLowerCase().includes(query) ||
        monitor.mid.toLowerCase().includes(query),
    );
  }, [monitors, search]);

  const visibleMonitors = useMemo(
    () => paginateMonitors(filteredMonitors, page, pageSize),
    [filteredMonitors, page, pageSize],
  );

  const totalPages = Math.max(1, Math.ceil(filteredMonitors.length / pageSize));

  if (!session) return null;

  return (
    <section className="panel live-panel">
      <header className="panel-header">
        <div>
          <h2>Live View</h2>
          <p>
            {PERFORMANCE_PRESETS[performanceMode].description} Showing{" "}
            {visibleMonitors.length} of {filteredMonitors.length} cameras.
          </p>
        </div>
        <div className="live-toolbar">
          <input
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(0);
            }}
            placeholder="Search camera name or ID"
          />
          <div className="pager">
            <button
              type="button"
              disabled={page === 0}
              onClick={() => setPage(Math.max(0, page - 1))}
            >
              Previous
            </button>
            <span>
              Page {page + 1} / {totalPages}
            </span>
            <button
              type="button"
              disabled={page + 1 >= totalPages}
              onClick={() => setPage(page + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </header>

      <div
        className="camera-grid"
        style={{ gridTemplateColumns: `repeat(${gridSize}, minmax(0, 1fr))` }}
      >
        {visibleMonitors.map((monitor) => (
          <CameraTile
            key={monitor.mid}
            session={session}
            monitorId={monitor.mid}
            name={monitor.name}
            selected={selectedMonitorId === monitor.mid}
            performanceMode={performanceMode}
            snapshotIntervalMs={snapshotIntervalMs}
            onSelect={() => setSelectedMonitorId(monitor.mid)}
          />
        ))}
      </div>
    </section>
  );
}
