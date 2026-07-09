import { io, Socket } from "socket.io-client";
import { socketPathFromUrl } from "./urls";
import type { ShinobiSession } from "./types";

export type ShinobiSocketEvent = {
  f?: string;
  [key: string]: unknown;
};

export class ShinobiSocket {
  private socket: Socket | null = null;

  connect(session: ShinobiSession, onEvent: (event: ShinobiSocketEvent) => void) {
    this.disconnect();

    this.socket = io(session.serverUrl, {
      transports: ["websocket"],
      path: socketPathFromUrl(session.serverUrl),
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
    });

    this.socket.on("connect", () => {
      this.socket?.emit("f", {
        f: "init",
        ke: session.groupKey,
        auth: session.authToken,
        uid: session.uid,
      });
    });

    this.socket.on("f", (payload: ShinobiSocketEvent) => {
      onEvent(payload);
    });

    this.socket.on("ping", () => {
      this.socket?.emit("pong", { beat: 1 });
    });

    return this.socket;
  }

  emit(event: ShinobiSocketEvent) {
    this.socket?.emit("f", event);
  }

  disconnect() {
    if (this.socket) {
      this.socket.removeAllListeners();
      this.socket.disconnect();
      this.socket = null;
    }
  }

  get connected(): boolean {
    return this.socket?.connected ?? false;
  }
}
