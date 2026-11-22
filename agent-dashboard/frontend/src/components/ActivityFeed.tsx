import { useEffect, useRef, useState } from "react";
import type { Entry, Step, Timeline } from "../parseLog";
import type { Phase } from "../types";

interface Filters {
  thoughts: boolean;
  observations: boolean;
}

interface Props {
  timeline: Timeline;
  phase: Phase;
}

const KIND_LABEL: Record<Entry["kind"], string> = {
  thought: "THINK",
  action: "ACT",
  observe: "SEE",
  finish: "DONE",
  heal: "RETRY",
  loop: "LOOP",
  info: "INFO",
};

export function ActivityFeed({ timeline, phase }: Props) {
  const [filters, setFilters] = useState<Filters>({ thoughts: true, observations: false });
  const scroller = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const entryCount = timeline.steps.reduce((total, step) => total + step.entries.length, 0);

  // Follow new activity while the user stays near the bottom.
  useEffect(() => {
    const element = scroller.current;
    if (element && stickToBottom.current) element.scrollTop = element.scrollHeight;
  }, [entryCount, timeline.steps.length]);

  const toggle = (name: keyof Filters) => setFilters((current) => ({ ...current, [name]: !current[name] }));

  return (
    <section className="card feed-card">
      <div className="feed-header">
        <h2>Agent activity</h2>
        <div className="chips">
          <button className={`chip ${filters.thoughts ? "on" : ""}`} onClick={() => toggle("thoughts")}>
            Thoughts
          </button>
          <button className={`chip ${filters.observations ? "on" : ""}`} onClick={() => toggle("observations")}>
            Observations
          </button>
        </div>
      </div>
      <div
        className="feed"
        ref={scroller}
        onScroll={(event) => {
          const el = event.currentTarget;
          stickToBottom.current = el.scrollTop + el.clientHeight >= el.scrollHeight - 60;
        }}
      >
        {timeline.steps.length === 0 && (
          <p className="empty">
            {phase === "running" ? "Planning test steps…" : 'Pick a ticket and press "Run agent". The agent\'s reasoning appears here live.'}
          </p>
        )}
        {timeline.steps.map((step, index) => (
          <StepCard
            key={step.key}
            step={step}
            filters={filters}
            live={phase === "running" && index === timeline.steps.length - 1}
          />
        ))}
        {timeline.notes.map((note, index) => (
          <p key={index} className="note">
            {note.text}
          </p>
        ))}
      </div>
    </section>
  );
}

function StepCard({ step, filters, live }: { step: Step; filters: Filters; live: boolean }) {
  const [openByUser, setOpenByUser] = useState<boolean | null>(null);
  const open = openByUser ?? (step.status !== "done" || live);
  const visible = step.entries.filter(
    (entry) => (entry.kind !== "thought" || filters.thoughts) && (entry.kind !== "observe" || filters.observations),
  );
  const status = live && step.status === "running" ? "running" : step.status;

  return (
    <article className={`step step-${status}`}>
      <button className="step-header" onClick={() => setOpenByUser(!open)} aria-expanded={open}>
        <span className={`dot dot-${status}`} />
        <span className="step-id">
          {step.criterionId} · {step.position}
        </span>
        <span className="step-instruction">{step.instruction}</span>
        {step.healed && <span className="tag tag-BLOCKED">self-healed</span>}
        <span className="chevron">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <ul className="entries">
          {visible.map((entry, index) => (
            <li key={index} className={`entry entry-${entry.kind} ${entry.ok === false ? "entry-failed" : ""}`}>
              <span className="time">{entry.time}</span>
              <span className="kind">{KIND_LABEL[entry.kind]}</span>
              <span className="text">{entry.text}</span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
