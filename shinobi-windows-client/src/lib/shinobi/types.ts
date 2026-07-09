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
  time: string | number;
  end?: string | number;
  duration?: number;
  size?: number;
  status?: number;
  details?: string | Record<string, unknown>;
  href?: string;
  links?: Record<string, string>;
}

export interface ShinobiVideoListResponse {
  total: number;
  limit: number;
  skip: number;
  isUTC?: boolean;
  videos: ShinobiVideo[];
}

export interface ShinobiEvent {
  ke: string;
  mid: string;
  time: string | number;
  details?: string | Record<string, unknown>;
}

export interface ShinobiAlarmItem {
  id: string;
  time: string;
  monitorId: string;
  monitorName?: string;
  message: string;
  level: "info" | "warning" | "critical";
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
