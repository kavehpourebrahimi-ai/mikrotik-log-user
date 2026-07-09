export interface ShinobiSession {
  serverUrl: string;
  authToken: string;
  groupKey: string;
  uid: string;
  mail: string;
  details: Record<string, unknown>;
}

export interface ShinobiMonitor {
  mid: string;
  ke: string;
  name: string;
  type?: string;
  ext?: string;
  mode?: string;
  width?: string;
  height?: string;
  details: string | Record<string, unknown>;
  snapshot?: string;
  streams?: string[];
  streamsSortedByType?: Record<string, string[]>;
  currentlyWatching?: number;
}

export interface ShinobiVideo {
  mid: string;
  ke: string;
  ext: string;
  time: number;
  duration?: number;
  size?: number;
  status?: number;
  details?: string;
}

export interface ShinobiLoginResponse {
  ok: boolean;
  auth_token?: string;
  ke?: string;
  uid?: string;
  mail?: string;
  details?: string | Record<string, unknown>;
}

export interface ShinobiUserInfo {
  ok: boolean;
  user?: {
    ke: string;
    uid: string;
    mail: string;
    auth_token: string;
    details: Record<string, unknown>;
  };
}

export type StreamType = "hls" | "flv" | "mjpeg" | "mp4" | "h264";

export interface ServerProfile {
  label: string;
  url: string;
}
