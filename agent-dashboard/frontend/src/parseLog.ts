// Turns the agent's flat log lines into a structured timeline: steps, entries and verdicts.
// Pure functions (no React), so the format knowledge lives in one place.

import type { LogEvent, Verdict } from "./types";

export type EntryKind = "thought" | "action" | "observe" | "finish" | "heal" | "loop" | "info";
export type StepStatus = "running" | "done" | "blocked";

export interface Entry {
  time: string;
  kind: EntryKind;
  text: string;
  ok?: boolean; // For actions: did the browser action succeed?
}

export interface Step {
  key: string; // e.g. "AC2.3"
  criterionId: string;
  position: string; // e.g. "3/5"
  instruction: string;
  status: StepStatus;
  healed: boolean;
  entries: Entry[];
}

export interface Timeline {
  plans: Record<string, string[]>;
  steps: Step[];
  results: Record<string, { verdict: Verdict; reason: string }>;
  notes: Entry[]; // Lines that belong to no step (planner warnings etc.)
}

const PLAN = /^PLAN (\S+?): (.*)$/s;
const STEP = /^\[(\S+)\] STEP (\d+)\/(\d+): (.*)$/s;
const LABELLED = /^\[(\S+\.\d+)\] (OBSERVE|THOUGHT|ACTION|FINISH|SELF-HEAL|LOOP DETECTED): ?(.*)$/s;
const LABELLED_INFO = /^\[(\S+\.\d+)\] (.*)$/s;
const RESULT = /^RESULT (\S+): (PASS|FAIL|BLOCKED) - (.*)$/s;
const FINISH = /^(done|blocked) - (.*)$/s;
const LOG_LINE = /^(\d\d:\d\d:\d\d) \| (.*)$/;

const KIND_BY_TAG: Record<string, EntryKind> = {
  OBSERVE: "observe",
  THOUGHT: "thought",
  ACTION: "action",
  FINISH: "finish",
  "SELF-HEAL": "heal",
  "LOOP DETECTED": "loop",
};

/** Parse the text of an agent.log file into events (a line without a timestamp continues the previous one). */
export function parseLogFile(text: string): LogEvent[] {
  const events: LogEvent[] = [];
  for (const line of text.split("\n")) {
    const match = line.replace(/\r$/, "").match(LOG_LINE);
    if (match) events.push({ time: match[1], text: match[2] });
    else if (events.length && line.trim()) events[events.length - 1].text += "\n" + line;
  }
  return events;
}

// "Gemini 503 UNAVAILABLE; retrying in 5s": routine API hiccups. They stay in agent.log but not in the UI.
const API_RETRY = /^Gemini .*; retrying in/;

export function buildTimeline(events: LogEvent[]): Timeline {
  const timeline: Timeline = { plans: {}, steps: [], results: {}, notes: [] };
  const stepsByKey = new Map<string, Step>();

  const stepFor = (key: string): Step => {
    let step = stepsByKey.get(key);
    if (!step) {
      step = { key, criterionId: key.split(".")[0], position: "", instruction: "", status: "running", healed: false, entries: [] };
      stepsByKey.set(key, step);
      timeline.steps.push(step);
    }
    return step;
  };

  for (const { time, text } of events) {
    let m: RegExpMatchArray | null;

    if ((m = text.match(PLAN))) {
      timeline.plans[m[1]] = m[2].split(" | ");
    } else if ((m = text.match(STEP))) {
      const step = stepFor(`${m[1]}.${m[2]}`);
      step.position = `${m[2]}/${m[3]}`;
      step.instruction = m[4];
    } else if ((m = text.match(LABELLED))) {
      addLabelled(stepFor(m[1]), time, m[2], m[3]);
    } else if ((m = text.match(RESULT))) {
      timeline.results[m[1]] = { verdict: m[2] as Verdict, reason: m[3] };
    } else if ((m = text.match(LABELLED_INFO))) {
      stepFor(m[1]).entries.push({ time, kind: "info", text: m[2] });
    } else if (!text.startsWith("OVERALL:") && !text.startsWith("Run ") && !API_RETRY.test(text)) {
      timeline.notes.push({ time, kind: "info", text });
    }
  }
  return timeline;
}

function addLabelled(step: Step, time: string, tag: string, body: string): void {
  const kind = KIND_BY_TAG[tag];
  const entry: Entry = { time, kind, text: body };

  if (kind === "action") {
    entry.ok = !body.includes("-> FAILED:");
  } else if (kind === "observe") {
    entry.text = `I see page ${body}`;
  } else if (kind === "heal") {
    step.healed = true;
    step.status = "running"; // The step gets a second attempt.
  } else if (kind === "finish") {
    const finish = body.match(FINISH);
    if (finish) {
      step.status = finish[1] === "done" ? "done" : "blocked";
      entry.text = finish[2];
    }
  }
  step.entries.push(entry);
}
