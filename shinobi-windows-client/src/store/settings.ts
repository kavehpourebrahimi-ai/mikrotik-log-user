export type PerformanceMode = "eco" | "balanced" | "performance";

export interface ClientSettings {
  performanceMode: PerformanceMode;
  snapshotIntervalMs: number;
  pageSize: number;
  autoFocusOnSelect: boolean;
}

export const DEFAULT_SETTINGS: ClientSettings = {
  performanceMode: "eco",
  snapshotIntervalMs: 2500,
  pageSize: 16,
  autoFocusOnSelect: true,
};

export const PERFORMANCE_PRESETS: Record<
  PerformanceMode,
  { label: string; description: string }
> = {
  eco: {
    label: "Eco (weak PCs)",
    description:
      "Snapshot refresh in the grid. Live video only in the focus panel.",
  },
  balanced: {
    label: "Balanced",
    description:
      "Snapshots in the grid, except the selected camera which streams live.",
  },
  performance: {
    label: "Performance",
    description:
      "Live HLS for every visible tile. Use only on strong workstations.",
  },
};
