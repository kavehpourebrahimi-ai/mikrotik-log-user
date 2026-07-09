import { useEffect, useRef, useState } from "react";
import { useHlsPlayer } from "../hooks/useHlsPlayer";
import { useSnapshotRefresh } from "../hooks/useSnapshotRefresh";
import { buildSnapshotUrl } from "../lib/shinobi/urls";
import type { PerformanceMode } from "../store/settings";
import type { ShinobiSession } from "../lib/shinobi/types";

interface CameraTileProps {
  session: ShinobiSession;
  monitorId: string;
  name: string;
  selected: boolean;
  performanceMode: PerformanceMode;
  snapshotIntervalMs: number;
  onSelect: () => void;
}

function shouldStreamTile(
  performanceMode: PerformanceMode,
  selected: boolean,
  visible: boolean,
) {
  if (!visible) return false;
  if (performanceMode === "performance") return true;
  if (performanceMode === "balanced") return selected;
  return false;
}

export function CameraTile({
  session,
  monitorId,
  name,
  selected,
  performanceMode,
  snapshotIntervalMs,
  onSelect,
}: CameraTileProps) {
  const containerRef = useRef<HTMLButtonElement>(null);
  const [visible, setVisible] = useState(false);
  const streamEnabled = shouldStreamTile(performanceMode, selected, visible);
  const videoRef = useHlsPlayer(session, monitorId, streamEnabled);
  const snapshotUrl = useSnapshotRefresh(
    session,
    monitorId,
    !streamEnabled && visible,
    snapshotIntervalMs,
  );

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        setVisible(entries.some((entry) => entry.isIntersecting));
      },
      { rootMargin: "80px" },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const fallbackSnapshot = buildSnapshotUrl(session, monitorId);

  return (
    <button
      ref={containerRef}
      type="button"
      className={`camera-tile ${selected ? "selected" : ""}`}
      onClick={onSelect}
    >
      <div className="camera-media">
        {streamEnabled ? (
          <video ref={videoRef} muted autoPlay playsInline />
        ) : visible ? (
          <img src={snapshotUrl} alt={name} loading="lazy" />
        ) : (
          <img src={fallbackSnapshot} alt={name} loading="lazy" />
        )}
      </div>
      <div className="camera-meta">
        <span>{name}</span>
        <small>{monitorId}</small>
      </div>
      {performanceMode === "eco" ? (
        <span className="camera-badge">ECO</span>
      ) : null}
    </button>
  );
}
