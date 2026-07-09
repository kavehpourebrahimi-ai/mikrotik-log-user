import { useEffect, useState } from "react";
import { buildSnapshotUrl } from "../lib/shinobi/urls";
import type { ShinobiSession } from "../lib/shinobi/types";

export function useSnapshotRefresh(
  session: ShinobiSession,
  monitorId: string,
  enabled: boolean,
  intervalMs: number,
) {
  const [snapshotUrl, setSnapshotUrl] = useState(() =>
    buildSnapshotUrl(session, monitorId),
  );

  useEffect(() => {
    if (!enabled) {
      setSnapshotUrl(buildSnapshotUrl(session, monitorId));
      return;
    }

    function refresh() {
      const base = buildSnapshotUrl(session, monitorId);
      setSnapshotUrl(`${base}?t=${Date.now()}`);
    }

    refresh();
    const timer = window.setInterval(refresh, intervalMs);
    return () => window.clearInterval(timer);
  }, [enabled, intervalMs, monitorId, session]);

  return snapshotUrl;
}
