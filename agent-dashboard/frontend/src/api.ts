import type { PastRun, Progress, RunDetails, Sample, StartResponse } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      /* body was not JSON; keep the status text */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

const post = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  samples: () => request<Sample[]>("/api/issues"),
  pastRuns: () => request<PastRun[]>("/api/runs"),
  runDetails: (runId: string) => request<RunDetails>(`/api/runs/${runId}`),
  progress: (since: number) => request<Progress>(`/api/progress?since=${since}`),
  githubIssue: (number: number) => request<{ number: number; markdown: string }>(`/api/github/issues/${number}`),
  startRun: (markdown: string, headed: boolean, issue: number | null = null, postResult = false) =>
    request<StartResponse>("/api/runs", post({ markdown, headed, issue, post: postResult })),
  stopRun: () => request<{ stopped: boolean }>("/api/stop", { method: "POST" }),
  async runLog(runId: string): Promise<string> {
    const response = await fetch(`/evidence/${runId}/agent.log`);
    return response.ok ? response.text() : "";
  },
};
