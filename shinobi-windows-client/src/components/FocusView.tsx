import { useHlsPlayer } from "../hooks/useHlsPlayer";
import type { ShinobiMonitor } from "../lib/shinobi/types";
import type { ShinobiSession } from "../lib/shinobi/types";

interface FocusViewProps {
  session: ShinobiSession;
  monitor: ShinobiMonitor | null;
  onClose: () => void;
}

export function FocusView({ session, monitor, onClose }: FocusViewProps) {
  const videoRef = useHlsPlayer(session, monitor?.mid ?? "", Boolean(monitor));

  if (!monitor) {
    return (
      <section className="focus-panel empty">
        <p>Select a camera to open the operator focus view.</p>
      </section>
    );
  }

  return (
    <section className="focus-panel">
      <header className="focus-header">
        <div>
          <p className="eyebrow">Operator Focus</p>
          <h2>{monitor.name}</h2>
          <small>{monitor.mid}</small>
        </div>
        <button type="button" onClick={onClose}>
          Close focus
        </button>
      </header>
      <div className="focus-media">
        <video ref={videoRef} controls autoPlay playsInline />
      </div>
    </section>
  );
}
