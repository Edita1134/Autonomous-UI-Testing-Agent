import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { ActivityFeed } from "./components/ActivityFeed";
import { CriteriaPanel } from "./components/CriteriaPanel";
import { Header } from "./components/Header";
import { RunHistory } from "./components/RunHistory";
import { Screenshots } from "./components/Screenshots";
import { TicketPanel } from "./components/TicketPanel";
import { formatDuration, useElapsed } from "./hooks/useElapsed";
import { useRun } from "./hooks/useRun";
import { useTheme } from "./hooks/useTheme";
import { buildTimeline } from "./parseLog";
import type { PastRun, Sample } from "./types";

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const [samples, setSamples] = useState<Sample[]>([]);
  const [pastRuns, setPastRuns] = useState<PastRun[]>([]);
  const [markdown, setMarkdown] = useState("");
  const [headed, setHeaded] = useState(false);
  const [githubIssue, setGithubIssue] = useState<number | null>(null);
  const [postResult, setPostResult] = useState(false);

  const refreshHistory = useCallback(() => {
    api.pastRuns().then(setPastRuns).catch(() => undefined);
  }, []);
  const { run, start, stop, openPast } = useRun(refreshHistory);

  useEffect(() => {
    refreshHistory();
    api
      .samples()
      .then((items) => {
        setSamples(items);
        setMarkdown((current) => current || items[0]?.markdown || "");
      })
      .catch(() => undefined);
  }, [refreshHistory]);

  const timeline = useMemo(() => buildTimeline(run.events), [run.events]);
  const running = run.phase === "running";
  const liveSeconds = useElapsed(run.startedAt, running);
  const elapsed = running
    ? formatDuration(liveSeconds)
    : run.details
      ? formatDuration(run.details.duration_seconds)
      : "";

  return (
    <>
      <Header phase={run.phase} overall={run.overall} elapsed={elapsed} theme={theme} onToggleTheme={toggleTheme} />
      <main className="layout">
        <div className="column">
          <TicketPanel
            samples={samples}
            markdown={markdown}
            githubIssue={githubIssue}
            postResult={postResult}
            headed={headed}
            running={running}
            error={run.phase === "error" && !run.runId ? run.error : ""}
            onMarkdownChange={(value) => {
              setMarkdown(value);
              setGithubIssue(null); // Hand-edited or sample text is run as text, not fetched from GitHub.
            }}
            onGithubLoaded={(issue, text) => {
              setMarkdown(text);
              setGithubIssue(issue);
            }}
            onPostResultChange={setPostResult}
            onHeadedChange={setHeaded}
            onRun={() => start(markdown, headed, githubIssue, githubIssue !== null && postResult)}
            onStop={stop}
          />
          <RunHistory runs={pastRuns} activeId={run.runId} disabled={running} onOpen={openPast} />
        </div>
        <ActivityFeed timeline={timeline} phase={run.phase} />
        <div className="column">
          <CriteriaPanel
            criteria={run.criteria}
            timeline={timeline}
            phase={run.phase}
            overall={run.overall}
            error={run.error}
            githubNote={run.githubNote}
            runId={run.runId}
            details={run.details}
          />
          <Screenshots urls={run.screenshots} />
        </div>
      </main>
    </>
  );
}
