// Shapes of the JSON returned by the Python backend (dashboard/app.py).

export type Verdict = "PASS" | "FAIL" | "BLOCKED";
export type Phase = "idle" | "running" | "done" | "error";

export interface LogEvent {
  time: string;
  text: string;
}

export interface Criterion {
  id: string;
  text: string;
}

export interface Progress {
  run_id: string;
  status: Phase;
  overall: Verdict | "";
  error: string;
  github_note: string; // Outcome of posting the result to GitHub ("" if not applicable).
  events: LogEvent[];
  next: number;
  screenshots: string[];
}

export interface StartResponse {
  run_id: string;
  criteria: Criterion[];
}

export interface PastRun {
  run_id: string;
  title: string;
  overall: Verdict;
  duration_seconds: number;
}

export interface CriterionReport {
  criterion: Criterion;
  verdict: Verdict;
  reason: string;
  evidence: string;
}

export interface RunDetails {
  run_id: string;
  title: string;
  target_url: string;
  overall: Verdict;
  model: string;
  duration_seconds: number;
  video_files: string[];
  screenshots: string[];
  results: CriterionReport[];
}

export interface Sample {
  name: string;
  markdown: string;
}
