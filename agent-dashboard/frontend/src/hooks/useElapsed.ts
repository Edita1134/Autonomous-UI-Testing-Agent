import { useEffect, useState } from "react";

/** Seconds since `startedAt`, ticking every second while `active`. */
export function useElapsed(startedAt: number | null, active: boolean): number {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [active]);

  return startedAt ? Math.max(0, Math.round(((active ? now : Date.now()) - startedAt) / 1000)) : 0;
}

export function formatDuration(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return minutes ? `${minutes}m ${String(seconds).padStart(2, "0")}s` : `${seconds}s`;
}
