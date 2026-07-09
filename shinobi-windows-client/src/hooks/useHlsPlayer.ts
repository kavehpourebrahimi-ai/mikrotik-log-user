import { useEffect, useRef } from "react";
import { buildStreamUrl } from "../lib/shinobi/urls";
import type { ShinobiSession, StreamType } from "../lib/shinobi/types";

type HlsInstance = {
  destroy: () => void;
  loadSource: (url: string) => void;
  attachMedia: (element: HTMLMediaElement) => void;
};

export function useHlsPlayer(
  session: ShinobiSession,
  monitorId: string,
  enabled: boolean,
  streamType: StreamType = "hls",
) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<HlsInstance | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !enabled) {
      hlsRef.current?.destroy();
      hlsRef.current = null;
      if (video) {
        video.removeAttribute("src");
        video.load();
      }
      return;
    }

    let cancelled = false;

    async function start() {
      const streamUrl = buildStreamUrl(session, monitorId, streamType);
      const HlsModule = await import("hls.js");
      if (cancelled || !video) return;

      if (HlsModule.default.isSupported()) {
        const hls = new HlsModule.default({
          enableWorker: true,
          lowLatencyMode: true,
          backBufferLength: 20,
          maxBufferLength: 12,
        });
        hlsRef.current = hls;
        hls.loadSource(streamUrl);
        hls.attachMedia(video);
        return;
      }

      video.src = streamUrl;
    }

    void start();

    return () => {
      cancelled = true;
      hlsRef.current?.destroy();
      hlsRef.current = null;
    };
  }, [enabled, monitorId, session, streamType]);

  return videoRef;
}
