import type { ShinobiSession, StreamType } from "./types";

export function normalizeServerUrl(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(trimmed)) {
    return `http://${trimmed}`;
  }
  return trimmed;
}

export function buildStreamUrl(
  session: ShinobiSession,
  monitorId: string,
  type: StreamType = "hls",
  channel?: string,
): string {
  const channelPart = channel ? `/${channel}` : "";
  const base = `${session.serverUrl}/${session.authToken}`;

  switch (type) {
    case "hls":
      return `${base}/hls/${session.groupKey}/${monitorId}${channelPart}/s.m3u8`;
    case "flv":
      return `${base}/flv/${session.groupKey}/${monitorId}${channelPart}/s.flv`;
    case "mjpeg":
      return `${base}/mjpeg/${session.groupKey}/${monitorId}${channelPart}`;
    case "mp4":
      return `${base}/mp4/${session.groupKey}/${monitorId}${channelPart}/s.mp4`;
    case "h264":
      return `${base}/h264/${session.groupKey}/${monitorId}${channelPart}`;
    default:
      return `${base}/hls/${session.groupKey}/${monitorId}/s.m3u8`;
  }
}

export function buildSnapshotUrl(
  session: ShinobiSession,
  monitorId: string,
): string {
  return `${session.serverUrl}/${session.authToken}/jpeg/${session.groupKey}/${monitorId}/s.jpg`;
}

export function buildVideoFileUrl(
  session: ShinobiSession,
  monitorId: string,
  file: string,
): string {
  return `${session.serverUrl}/${session.authToken}/videos/${session.groupKey}/${monitorId}/${file}`;
}

export function socketPathFromUrl(serverUrl: string): string {
  try {
    const pathname = new URL(serverUrl).pathname.replace(/\/+$/, "");
    return `${pathname || ""}/socket.io`;
  } catch {
    return "/socket.io";
  }
}
