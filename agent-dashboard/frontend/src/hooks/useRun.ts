import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { parseLogFile } from "../parseLog";
import type { Criterion, LogEvent, Phase, RunDetails, Verdict } from "../types";

const POLL_INTERVAL_MS = 800;

/** Everything the UI needs about the run being shown (a live run or an opened past run). */
export interface RunState {
  phase: Phase;
  runId: string;
  events: LogEvent[];
  criteria: Criterion[];
  screenshots: string[];
  overall: Verdict | "";
  error: string;
  githubNote: string; // What happened when posting the result to the GitHub issue.
  startedAt: number | null;
  details: RunDetails | null; // Final report, once the run has finished.
}

const EMPTY: RunState = {
  phase: "idle",
  runId: "",
  events: [],
  criteria: [],
  screenshots: [],
  overall: "",
  error: "",
  githubNote: "",
  startedAt: null,
  details: null,
};

export function useRun(onFinished: () => void) {
  const [run, setRun] = useState<RunState>(EMPTY);
  const since = useRef(0); // How many log events we already have.
  const polling = useRef(false); // Prevents overlapping requests if the server is slow.

  const poll = useCallback(async () => {
    if (polling.current) return;
    polling.current = true;
    try {
      const progress = await api.progress(since.current);
      since.current = progress.next;
      const finished = progress.status === "done" || progress.status === "error";
      const details = progress.status === "done" ? await api.runDetails(progress.run_id).catch(() => null) : null;

      setRun((previous) => ({
        ...previous,
        phase: progress.status === "idle" ? previous.phase : progress.status,
        runId: progress.run_id,
        events: progress.events.length ? [...previous.events, ...progress.events] : previous.events,
        screenshots: progress.screenshots,
        overall: progress.overall,
        error: progress.error,
        githubNote: progress.github_note,
        details,
      }));
      if (finished) onFinished();
    } catch (error) {
      setRun((previous) => ({ ...previous, phase: "error", error: String(error) }));
    } finally {
      polling.current = false;
    }
  }, [onFinished]);

  useEffect(() => {
    if (run.phase !== "running") return;
    const timer = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [run.phase, poll]);

  const start = useCallback(async (markdown: string, headed: boolean, issue: number | null, postResult: boolean) => {
    since.current = 0;
    try {
      const { criteria } = await api.startRun(markdown, headed, issue, postResult);
      setRun({ ...EMPTY, phase: "running", criteria, startedAt: Date.now() });
    } catch (error) {
      setRun({ ...EMPTY, phase: "error", error: error instanceof Error ? error.message : String(error) });
    }
  }, []);

  const stop = useCallback(() => api.stopRun().catch(() => undefined), []);

  const openPast = useCallback(async (runId: string) => {
    const [details, log] = await Promise.all([api.runDetails(runId), api.runLog(runId)]);
    since.current = 0;
    setRun({
      ...EMPTY,
      phase: "done",
      runId,
      events: parseLogFile(log),
      criteria: details.results.map((result) => result.criterion),
      screenshots: details.screenshots,
      overall: details.overall,
      details,
    });
  }, []);

  return { run, start, stop, openPast };
}
