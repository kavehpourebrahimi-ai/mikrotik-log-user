import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  DEFAULT_SETTINGS,
  type ClientSettings,
  type PerformanceMode,
} from "./settings";

interface SettingsState extends ClientSettings {
  setPerformanceMode: (mode: PerformanceMode) => void;
  setSnapshotIntervalMs: (value: number) => void;
  setPageSize: (value: number) => void;
  setAutoFocusOnSelect: (value: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...DEFAULT_SETTINGS,

      setPerformanceMode: (performanceMode) => set({ performanceMode }),
      setSnapshotIntervalMs: (snapshotIntervalMs) =>
        set({ snapshotIntervalMs }),
      setPageSize: (pageSize) => set({ pageSize }),
      setAutoFocusOnSelect: (autoFocusOnSelect) => set({ autoFocusOnSelect }),
    }),
    { name: "shinobi-client-settings" },
  ),
);
