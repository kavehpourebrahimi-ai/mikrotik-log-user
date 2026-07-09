import { create } from "zustand";
import type { ShinobiAlarmItem } from "../lib/shinobi/types";

interface AlarmState {
  alarms: ShinobiAlarmItem[];
  pushAlarm: (alarm: ShinobiAlarmItem) => void;
  clearAlarms: () => void;
}

const MAX_ALARMS = 100;

export const useAlarmStore = create<AlarmState>((set) => ({
  alarms: [],

  pushAlarm: (alarm) =>
    set((state) => ({
      alarms: [alarm, ...state.alarms].slice(0, MAX_ALARMS),
    })),

  clearAlarms: () => set({ alarms: [] }),
}));

export function mapSocketEventToAlarm(
  event: Record<string, unknown>,
  monitorName?: string,
): ShinobiAlarmItem | null {
  const code = String(event.f ?? "event");
  const monitorId = String(event.mid ?? event.id ?? "unknown");
  const level =
    code.includes("delete") || code.includes("error")
      ? "critical"
      : code.includes("video") || code.includes("motion")
        ? "warning"
        : "info";

  return {
    id: `${code}-${monitorId}-${Date.now()}`,
    time: new Date().toLocaleTimeString(),
    monitorId,
    monitorName,
    message: code.replace(/_/g, " "),
    level,
  };
}
