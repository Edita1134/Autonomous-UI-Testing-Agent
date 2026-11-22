import { formatDuration } from "../hooks/useElapsed";
import type { PastRun } from "../types";

interface Props {
  runs: PastRun[];
  activeId: string;
  disabled: boolean;
  onOpen: (runId: string) => void;
}

export function RunHistory({ runs, activeId, disabled, onOpen }: Props) {
  return (
    <section className="card">
      <h2>Past runs</h2>
      {runs.length === 0 && <p className="empty">No runs yet</p>}
      <ul className="history">
        {runs.map((run) => (
          <li key={run.run_id}>
            <button className={run.run_id === activeId ? "active" : ""} disabled={disabled} onClick={() => onOpen(run.run_id)}>
              <span className={`dot dot-${run.overall}`} />
              <span className="history-title">
                {run.title || run.run_id}
                <small>
                  {run.run_id.replace("run-", "")} · {formatDuration(run.duration_seconds)}
                </small>
              </span>
              <span className={`tag tag-${run.overall}`}>{run.overall}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
