import { useEffect, useRef, useState } from "react";
import Hls from "hls.js";
import type { ShinobiSession } from "../lib/shinobi/types";
import { buildSnapshotUrl, buildStreamUrl } from "../lib/shinobi/urls";

interface CameraTileProps {
  session: ShinobiSession;
  monitorId: string;
  name: string;
  active: boolean;
  selected: boolean;
  onSelect: () => void;
}

export function CameraTile({
  session,
  monitorId,
  name,
  active,
  selected,
  onSelect,
}: CameraTileProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLButtonElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const [visible, setVisible] = useState(false);
  const [streamError, setStreamError] = useState(false);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        setVisible(entries.some((entry) => entry.isIntersecting));
      },
      { rootMargin: "120px" },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !active || !visible) {
      hlsRef.current?.destroy();
      hlsRef.current = null;
      if (video) {
        video.removeAttribute("src");
        video.load();
      }
      return;
    }

    const streamUrl = buildStreamUrl(session, monitorId, "hls");
    setStreamError(false);

    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 30,
        maxBufferLength: 15,
      });
      hlsRef.current = hls;
      hls.loadSource(streamUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          setStreamError(true);
        }
      });
      return () => {
        hls.destroy();
        hlsRef.current = null;
      };
    }

    video.src = streamUrl;
    return undefined;
  }, [active, monitorId, session, visible]);

  const snapshotUrl = buildSnapshotUrl(session, monitorId);

  return (
    <button
      ref={containerRef}
      type="button"
      className={`camera-tile ${selected ? "selected" : ""}`}
      onClick={onSelect}
    >
      <div className="camera-media">
        {active && visible && !streamError ? (
          <video ref={videoRef} muted autoPlay playsInline />
        ) : (
          <img src={snapshotUrl} alt={name} loading="lazy" />
        )}
      </div>
      <div className="camera-meta">
        <span>{name}</span>
        <small>{monitorId}</small>
      </div>
    </button>
  );
}
