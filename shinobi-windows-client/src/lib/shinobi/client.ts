import {
  normalizeServerUrl,
} from "./urls";
import type {
  ShinobiEvent,
  ShinobiLoginResponse,
  ShinobiMonitor,
  ShinobiSession,
  ShinobiUserInfo,
  ShinobiVideo,
  ShinobiVideoListResponse,
} from "./types";

export class ShinobiApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ShinobiApiError";
    this.status = status;
  }
}

function parseDetails(details: string | Record<string, unknown> | undefined) {
  if (!details) return {};
  if (typeof details === "string") {
    try {
      return JSON.parse(details) as Record<string, unknown>;
    } catch {
      return {};
    }
  }
  return details;
}

export class ShinobiClient {
  constructor(private session: ShinobiSession) {}

  static async login(
    serverUrl: string,
    mail: string,
    password: string,
  ): Promise<ShinobiSession> {
    const normalized = normalizeServerUrl(serverUrl);
    const response = await fetch(`${normalized}/?json=true`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        mail,
        pass: password,
        function: "dash",
      }),
    });

    if (!response.ok) {
      throw new ShinobiApiError(
        `Login failed with HTTP ${response.status}`,
        response.status,
      );
    }

    const payload = (await response.json()) as ShinobiLoginResponse;
    if (!payload.ok || !payload.auth_token || !payload.ke || !payload.uid) {
      throw new ShinobiApiError("Invalid email or password");
    }

    return {
      serverUrl: normalized,
      authToken: payload.auth_token,
      groupKey: payload.ke,
      uid: payload.uid,
      mail: payload.mail ?? mail,
      details: parseDetails(payload.details),
    };
  }

  withSession(session: ShinobiSession): ShinobiClient {
    return new ShinobiClient(session);
  }

  get sessionInfo(): ShinobiSession {
    return this.session;
  }

  private apiUrl(path: string): string {
    return `${this.session.serverUrl}/${this.session.authToken}${path}`;
  }

  private async getJson<T>(path: string): Promise<T> {
    const response = await fetch(this.apiUrl(path), {
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new ShinobiApiError(
        `Request failed: ${path} (${response.status})`,
        response.status,
      );
    }

    return (await response.json()) as T;
  }

  async getUserInfo(): Promise<ShinobiUserInfo> {
    return this.getJson<ShinobiUserInfo>(
      `/userInfo/${this.session.groupKey}`,
    );
  }

  async listMonitors(): Promise<ShinobiMonitor[]> {
    const payload = await this.getJson<ShinobiMonitor | ShinobiMonitor[]>(
      `/monitor/${this.session.groupKey}`,
    );
    return Array.isArray(payload) ? payload : [payload];
  }

  async listVideos(
    monitorId?: string,
    limit = "50",
  ): Promise<ShinobiVideoListResponse> {
    const query = limit ? `?limit=${encodeURIComponent(limit)}` : "";
    const path = monitorId
      ? `/videos/${this.session.groupKey}/${monitorId}${query}`
      : `/videos/${this.session.groupKey}${query}`;
    const payload = await this.getJson<
      ShinobiVideoListResponse | ShinobiVideo | ShinobiVideo[]
    >(path);

    if (Array.isArray(payload)) {
      return { total: payload.length, limit: payload.length, skip: 0, videos: payload };
    }

    if ("videos" in payload) {
      return payload;
    }

    return { total: 1, limit: 1, skip: 0, videos: [payload] };
  }

  async listEvents(monitorId?: string, limit = "30"): Promise<ShinobiEvent[]> {
    const path = monitorId
      ? `/events/${this.session.groupKey}/${monitorId}/${limit}`
      : `/events/${this.session.groupKey}`;
    const payload = await this.getJson<ShinobiEvent | ShinobiEvent[]>(path);
    return Array.isArray(payload) ? payload : [payload];
  }

  videoUrl(video: ShinobiVideo): string {
    if (video.href) {
      return `${this.session.serverUrl}${video.href}`;
    }
    return `${this.session.serverUrl}/${this.session.authToken}/videos/${this.session.groupKey}/${video.mid}/${video.time}.${video.ext}`;
  }

  async ptzControl(monitorId: string, direction: string): Promise<void> {
    const response = await fetch(
      this.apiUrl(
        `/control/${this.session.groupKey}/${monitorId}/${direction}`,
      ),
      { headers: { Accept: "application/json" } },
    );
    if (!response.ok) {
      throw new ShinobiApiError("PTZ command failed", response.status);
    }
  }
}
