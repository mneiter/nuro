"use client";

import { useEffect, useMemo, useState } from "react";

import type { TimerTickState } from "../hooks/useTimer";

interface TimerDisplayProps {
  timer: TimerTickState | null;
}

function formatTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const seconds = Math.floor(totalSeconds % 60)
    .toString()
    .padStart(2, "0");
  return `${minutes}:${seconds}`;
}

const statusLabels: Record<string, string> = {
  running: "Running",
  completed: "Completed",
  canceled: "Canceled"
};

export default function TimerDisplay({ timer }: TimerDisplayProps) {
  const [displaySeconds, setDisplaySeconds] = useState(timer?.remainingSeconds ?? 0);

  useEffect(() => {
    if (!timer) {
      setDisplaySeconds(0);
      return;
    }

    const syncFromTimer = () => {
      const elapsed = Math.floor((Date.now() - timer.lastSyncedAt) / 1000);
      const remaining = Math.max(0, timer.remainingSeconds - elapsed);
      setDisplaySeconds(remaining);
    };

    syncFromTimer();

    if (timer.status !== "running") {
      return;
    }

    const intervalId = window.setInterval(syncFromTimer, 1000);
    return () => window.clearInterval(intervalId);
  }, [timer]);

  const formattedTime = useMemo(() => formatTime(displaySeconds), [displaySeconds]);
  const statusText = timer ? statusLabels[timer.status] ?? timer.status : "Idle";

  if (!timer) {
    return (
      <div className="timer-card">
        <span>No active timer yet.</span>
      </div>
    );
  }

  return (
    <div className="timer-card">
      <h2>{formattedTime}</h2>
      <span>{statusText}</span>
    </div>
  );
}
