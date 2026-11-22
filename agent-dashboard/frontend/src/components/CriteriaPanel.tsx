import type { Timeline } from "../parseLog";
import type { Criterion, Phase, RunDetails, Verdict } from "../types";
import { formatDuration } from "../hooks/useElapsed";

interface Props {
  criteria: Criterion[];
  timeline: Timeline;
  phase: Phase;
  overall: Verdict | "";
  error: string;
  githubNote: string;
  runId: string;
  details: RunDetails | null;
}

type CardState = "pending" | "running" | Verdict;

export function CriteriaPanel({ criteria, timeline, phase, overall, error, githubNote, runId, details }: Props) {
  const activeId = timeline.steps[timeline.steps.length - 1]?.criterionId;
  const stateOf = (id: string): CardState => {
    const result = timeline.results[id];
    if (result) return result.verdict;
    return phase === "running" && id === activeId ? "running" : "pending";
  };
  const finished = criteria.filter((criterion) => timeline.results[criterion.id]).length;
  const percent = criteria.length ? Math.round((finished / criteria.length) * 100) : 0;

  return (
    <section className="card">
      <h2>Acceptance criteria</h2>
      {phase === "done" && overall && (
        <div className={`banner banner-${overall}`}>
          <strong>Overall: {overall}</strong>
          {details && (
            <small>
              {formatDuration(details.duration_seconds)} · {details.model}
            </small>
          )}
        </div>
      )}
      {githubNote && (
        <p className={githubNote.startsWith("Warning") ? "error-box" : "note github-note"}>{githubNote}</p>
      )}
      {phase === "error" && error && runId && <div className="error-box">{error}</div>}

      {criteria.length > 0 && (
        <div className="progress" title={`${finished} of ${criteria.length} criteria judged`}>
          <div className="progress-bar" style={{ width: `${percent}%` }} />
        </div>
      )}
      {criteria.length === 0 && <p className="empty">Nothing running</p>}

      <ul className="criteria">
        {criteria.map((criterion) => {
          const state = stateOf(criterion.id);
          const result = timeline.results[criterion.id];
          return (
            <li key={criterion.id} className={`criterion criterion-${state}`}>
              <div className="criterion-head">
                <strong>{criterion.id}</strong>
                <span className={`tag tag-${state}`}>{state === "running" ? "Testing…" : state}</span>
              </div>
              <p className="criterion-text">{criterion.text}</p>
              {result && <p className="criterion-reason">{result.reason}</p>}
            </li>
          );
        })}
      </ul>

      {phase === "done" && details && runId && (
        <div className="links">
          {details.video_files.map((file) => (
            <a key={file} href={`/evidence/${runId}/${file}`} target="_blank" rel="noreferrer">
              ▶ Recording
            </a>
          ))}
          <a href={`/evidence/${runId}/report.md`} target="_blank" rel="noreferrer">
            ⤓ Report
          </a>
          <a href={`/evidence/${runId}/agent.log`} target="_blank" rel="noreferrer">
            ☰ Full log
          </a>
        </div>
      )}
    </section>
  );
}
