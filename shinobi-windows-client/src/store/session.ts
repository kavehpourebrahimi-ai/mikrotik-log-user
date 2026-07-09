import { create } from "zustand";
import { persist } from "zustand/middleware";
import { ShinobiClient } from "../lib/shinobi/client";
import type { ServerProfile, ShinobiSession } from "../lib/shinobi/types";

interface SessionState {
  session: ShinobiSession | null;
  client: ShinobiClient | null;
  savedServers: ServerProfile[];
  status: "idle" | "connecting" | "connected" | "error";
  error: string | null;
  login: (serverUrl: string, mail: string, password: string) => Promise<void>;
  logout: () => void;
  addSavedServer: (profile: ServerProfile) => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      session: null,
      client: null,
      savedServers: [],
      status: "idle",
      error: null,

      login: async (serverUrl, mail, password) => {
        set({ status: "connecting", error: null });
        try {
          const session = await ShinobiClient.login(serverUrl, mail, password);
          const client = new ShinobiClient(session);
          set({
            session,
            client,
            status: "connected",
            error: null,
          });
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "Connection failed";
          set({
            session: null,
            client: null,
            status: "error",
            error: message,
          });
          throw error;
        }
      },

      logout: () => {
        set({
          session: null,
          client: null,
          status: "idle",
          error: null,
        });
      },

      addSavedServer: (profile) => {
        set((state) => {
          const exists = state.savedServers.some(
            (entry) => entry.url === profile.url,
          );
          if (exists) return state;
          return { savedServers: [...state.savedServers, profile] };
        });
      },
    }),
    {
      name: "shinobi-client-session",
      partialize: (state) => ({
        savedServers: state.savedServers,
      }),
    },
  ),
);
