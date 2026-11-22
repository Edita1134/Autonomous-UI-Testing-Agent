# Architecture

How a ticket in "Ready for QA" (RFQA) becomes a PASS / FAIL verdict with evidence.

## System overview

![Architecture overview: triggers, agent pipeline, external systems and output](img/architecture-overview.svg)

PNG copy for slides and PDFs: [img/architecture-overview.png](img/architecture-overview.png). The purple, blue, orange and green boxes are triggers, agent pipeline, external systems and output; the **LLM** tag marks the three steps that call Gemini.

## One run, step by step

```mermaid
sequenceDiagram
    autonumber
    participant U as Trigger (label, CLI, dashboard)
    participant R as Runner
    participant P as Planner
    participant X as Executor
    participant B as Browser
    participant L as Gemini
    participant V as Verifier
    participant G as GitHub issue

    U->>R: ticket number or file
    R->>G: fetch issue (title, body)
    R->>R: parse Acceptance Criteria and Target URL
    R->>P: criteria
    P->>L: "write atomic test steps" (JSON)
    L-->>P: steps per criterion
    R->>B: open target URL

    loop each criterion, each step
        loop at most 8 actions
            X->>B: snapshot (URL, title, ARIA tree)
            X->>L: step + snapshot + actions so far
            L-->>X: tool call (click / fill / navigate / finish_step)
            X->>B: run action by role + accessible name
            B-->>X: outcome or error
            Note over X: LoopGuard: same action and page 3 times<br/>means warn, then abort
        end
        Note over X: step blocked? retry once with the failure reason (self-heal)
    end

    R->>V: criterion, steps, final snapshot
    V->>L: "judge this criterion" (JSON)
    L-->>V: verdict + quoted evidence
    Note over V: evidence not found on the page<br/>means the verdict is downgraded to BLOCKED
    V-->>R: PASS / FAIL / BLOCKED + reason

    R->>R: write report.md and report.json (evidence folder)
    R->>G: comment the report, add qa-passed / qa-failed / qa-blocked
```

## Key design decisions

| Decision | Why |
|----------|-----|
| The page is shown to the model as an ARIA tree, and elements are named by **role + accessible name** | No CSS or XPath selectors, so tests survive markup changes. This is how a human describes a page. |
| **Planner, Executor and Verifier are separate LLM roles** with narrow prompts | The model that performs a step never judges it, which reduces self-confirming mistakes. |
| Verdict **evidence must appear verbatim** in what the agent observed | Guards against hallucinated results: an ungrounded PASS or FAIL becomes BLOCKED. |
| **Hard limits in code**, not only in prompts (8 actions per step, loop guard, one retry) | A runaway or confused model cannot loop forever. |
| The dashboard only **starts the agent CLI and reads its files** | The two projects stay decoupled; the agent works without the UI. |
