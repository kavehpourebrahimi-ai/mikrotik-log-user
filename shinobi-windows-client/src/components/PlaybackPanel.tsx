import { useEffect, useState } from "react";
import type { ShinobiClient } from "../lib/shinobi/client";
import type { ShinobiMonitor, ShinobiVideo } from "../lib/shinobi/types";

interface PlaybackPanelProps {
  client: ShinobiClient;
  monitor: ShinobiMonitor | null;
}

export function PlaybackPanel({ client, monitor }: PlaybackPanelProps) {
  const [videos, setVideos] = useState<ShinobiVideo[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<ShinobiVideo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!monitor) {
      setVideos([]);
      setSelectedVideo(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    client
      .listVideos(monitor.mid, "40")
      .then((response) => {
        if (!cancelled) {
          setVideos(response.videos);
          setSelectedVideo(response.videos[0] ?? null);
          setError(null);
        }
      })
      .catch((loadError: Error) => {
        if (!cancelled) setError(loadError.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [client, monitor]);

  if (!monitor) {
    return (
      <section className="panel">
        <header className="panel-header">
          <div>
            <h2>Playback</h2>
            <p>Select a camera from Live View to review recordings.</p>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section className="panel playback-panel">
      <header className="panel-header">
        <div>
          <h2>Playback</h2>
          <p>
            Recordings for <strong>{monitor.name}</strong> are loaded directly
            from the Shinobi server storage.
          </p>
        </div>
      </header>

      {loading ? <p className="status-line">Loading recordings...</p> : null}
      {error ? <p className="form-error">{error}</p> : null}

      <div className="playback-layout">
        <div className="recording-list">
          {videos.length === 0 && !loading ? (
            <p className="status-line">No recordings found for this camera.</p>
          ) : null}
          {videos.map((video) => (
            <button
              key={`${video.mid}-${video.time}`}
              type="button"
              className={`recording-item ${
                selectedVideo?.time === video.time ? "active" : ""
              }`}
              onClick={() => setSelectedVideo(video)}
            >
              <strong>{String(video.time)}</strong>
              <span>{video.ext?.toUpperCase()}</span>
              {video.size ? <small>{Math.round(video.size / 1024 / 1024)} MB</small> : null}
            </button>
          ))}
        </div>

        <div className="recording-player">
          {selectedVideo ? (
            <>
              <video
                key={client.videoUrl(selectedVideo)}
                controls
                autoPlay
                src={client.videoUrl(selectedVideo)}
              />
              <div className="recording-meta">
                <span>{String(selectedVideo.time)}</span>
                <span>{selectedVideo.ext}</span>
              </div>
            </>
          ) : (
            <div className="placeholder-card">
              <p>Choose a recording to start playback.</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
