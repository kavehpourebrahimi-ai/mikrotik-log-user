import { create } from "zustand";
import type { ShinobiMonitor } from "../lib/shinobi/types";

interface MonitorState {
  monitors: ShinobiMonitor[];
  selectedMonitorId: string | null;
  loading: boolean;
  error: string | null;
  gridSize: 4 | 6 | 8 | 10 | 16;
  page: number;
  pageSize: number;
  setMonitors: (monitors: ShinobiMonitor[]) => void;
  setSelectedMonitorId: (monitorId: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setGridSize: (size: 4 | 6 | 8 | 10 | 16) => void;
  setPage: (page: number) => void;
}

export const useMonitorStore = create<MonitorState>((set) => ({
  monitors: [],
  selectedMonitorId: null,
  loading: false,
  error: null,
  gridSize: 8,
  page: 0,
  pageSize: 64,

  setMonitors: (monitors) => set({ monitors }),
  setSelectedMonitorId: (monitorId) => set({ selectedMonitorId: monitorId }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  setGridSize: (gridSize) => set({ gridSize, page: 0 }),
  setPage: (page) => set({ page }),
}));

export function paginateMonitors(
  monitors: ShinobiMonitor[],
  page: number,
  pageSize: number,
) {
  const start = page * pageSize;
  return monitors.slice(start, start + pageSize);
}
