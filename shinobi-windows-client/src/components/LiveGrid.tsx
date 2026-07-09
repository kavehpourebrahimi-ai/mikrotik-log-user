import { useMemo } from "react";
import { paginateMonitors, useMonitorStore } from "../store/monitors";
import { useSessionStore } from "../store/session";
import { CameraTile } from "./CameraTile";

export function LiveGrid() {
  const session = useSessionStore((state) => state.session);
  const monitors = useMonitorStore((state) => state.monitors);
  const gridSize = useMonitorStore((state) => state.gridSize);
  const page = useMonitorStore((state) => state.page);
  const pageSize = useMonitorStore((state) => state.pageSize);
  const selectedMonitorId = useMonitorStore((state) => state.selectedMonitorId);
  const setSelectedMonitorId = useMonitorStore(
    (state) => state.setSelectedMonitorId,
  );
  const setPage = useMonitorStore((state) => state.setPage);

  const visibleMonitors = useMemo(
    () => paginateMonitors(monitors, page, pageSize),
    [monitors, page, pageSize],
  );

  const totalPages = Math.max(1, Math.ceil(monitors.length / pageSize));

  if (!session) return null;

  return (
    <section className="panel live-panel">
      <header className="panel-header">
        <div>
          <h2>Live View</h2>
          <p>
            Showing {visibleMonitors.length} of {monitors.length} cameras. Only
            visible tiles decode video to keep the client responsive at scale.
          </p>
        </div>
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
            active
            selected={selectedMonitorId === monitor.mid}
            onSelect={() => setSelectedMonitorId(monitor.mid)}
          />
        ))}
      </div>
    </section>
  );
}
