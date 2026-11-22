import type { Phase, Verdict } from "../types";

interface Props {
  phase: Phase;
  overall: Verdict | "";
  elapsed: string;
  theme: "dark" | "light";
  onToggleTheme: () => void;
}

const LABELS: Record<Phase, string> = { idle: "Idle", running: "Running", done: "Finished", error: "Stopped" };

export function Header({ phase, overall, elapsed, theme, onToggleTheme }: Props) {
  const tone = phase === "done" && overall ? overall : phase;
  return (
    <header className="header">
      <div className="brand">
        <span className="logo" aria-hidden>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12.5l4.5 4.5L19 7.5" />
          </svg>
        </span>
        <div>
          <h1>UI Test Agent</h1>
          <p>GitHub issue → plan → browser → verdict</p>
        </div>
      </div>
      <div className="header-right">
        {elapsed && <span className="elapsed">{elapsed}</span>}
        <span className={`pill pill-${tone}`}>
          {phase === "running" && <span className="spinner" />}
          {phase === "done" && overall ? overall : LABELS[phase]}
        </span>
        <button className="icon-button" onClick={onToggleTheme} title="Toggle light/dark theme">
          {theme === "dark" ? "☀" : "☾"}
        </button>
      </div>
    </header>
  );
}
