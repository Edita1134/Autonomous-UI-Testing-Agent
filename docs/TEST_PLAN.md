# Test Plan & Strategy

> Diagrams of the architecture and of one run: [ARCHITECTURE.md](ARCHITECTURE.md).

## 1. Architecture: how the LLM drives the browser

```
GitHub issue (label RFQA)  --webhook / Action / CLI-->  tickets/parser
                                                            |
                                                         Planner (LLM, JSON)      ACs -> natural-language steps
                                                            |
                      +-------------------------------------+------------------------------+
                      | for each scenario, for each step:                                  |
                      |   Executor loop:  OBSERVE (ARIA snapshot) -> THINK + ACT (tool call)|
                      |                   -> Playwright runs it -> repeat                  |
                      +-------------------------------------+------------------------------+
                                                            |
                                                  Verifier (separate LLM call)   judges the AC
                                                            |
                                                  Reporter -> report.md/json, issue comment, labels
```

- **LLM:** Gemini Developer API (default `gemini-3.5-flash-lite`) with native function calling and JSON mode (`agent/llm/client.py`). Temperature 0.
- **Browser:** Playwright (Chromium). The model never writes code; it can only call five tools:
  `navigate`, `click`, `fill`, `press_key`, `finish_step` (`agent/llm/tool_schemas.py`).
- **Loop:** each turn the model receives the step goal, a compact log of its actions in this step, and the *current*
  page snapshot only. Old snapshots are dropped, which keeps tokens low enough for Gemini free-tier rate limits and keeps the
  model focused on the present state.
- **Why my own loop instead of a framework:** the assignment values how LLM unpredictability is handled. A ~100-line
  loop makes every guardrail explicit and testable, and avoids framework abstractions hiding behaviour.

## 2. Element identification and assertions

**Identification.** The page is given to the LLM as an ARIA accessibility tree (`button "Login"`,
`textbox "Username"`). The model names an element by *role + accessible name*; Playwright resolves it with
`get_by_role`. No CSS/XPath/ids anywhere. Why: accessible names are what users perceive, they survive refactors, and
the text form is far cheaper and more reliable than pixel coordinates for an open model.

When several elements match (e.g. six "Add to cart" buttons), the tool refuses to guess and returns an error telling
the model to add `within_text` (nearby text such as the product name). There is deliberately no `nth` index option: in testing, the model passed `nth=0` by default and silently clicked the wrong item. The model recovers from the error
rather than clicking the wrong thing.

**Assertions.** Acting and judging are separated:
1. The *executor* only performs steps and is told not to judge the application.
2. The *verifier* is a fresh LLM call that sees only the AC, the action log and the final snapshot.
3. For PASS or FAIL it must quote a few words from the page. Code checks the quote appears verbatim in the real
   snapshot or tool outcomes (`verifier.is_grounded`). An ungrounded verdict is downgraded to BLOCKED.
   The executor's own prose summaries are *not* accepted as proof, because they are LLM text.

Verdicts: **PASS** (met, proven), **FAIL** (the app is wrong), **BLOCKED** (the agent could not conclude, e.g. could
not reach the page). Keeping FAIL and BLOCKED apart stops agent trouble from being reported as an app bug.

## 3. Preventing infinite loops and hallucination

Prompts alone are not trusted; every rule has a code-level backstop.

| Risk | Prompt rule | Code enforcement |
|------|-------------|------------------|
| Endless clicking | "Never repeat a failing action more than twice" | Hard cap of 8 actions per step (`max_actions_per_step`) |
| Repeating with no progress | "Do something different" | `LoopGuard`: same action + same page fingerprint 3 times -> warning injected into the prompt; once more -> step aborted |
| Inventing elements | "Only use elements in the CURRENT snapshot" | Tools fail with a clear error if the element does not exist; unknown tools are rejected |
| Never finishing | `finish_step` tool with `done`/`blocked` | `tool_choice="required"` so every turn is a tool call; budget abort otherwise |
| Malformed tool calls (common in open models) | - | Caught and recorded as a failed action; the loop continues |
| Hallucinated verdict | "Quote exact evidence" | Evidence must be found verbatim in observations, else BLOCKED |
| Silently skipped AC | - | Planner output is validated; a missing AC falls back to its raw text |
| Rate limits (Gemini free tier) | - | Retry with exponential backoff |

## 4. Error handling and self-healing

- A step that cannot be completed stops its scenario (later steps depend on it) and the report says which step
  and why, in the agent's words, plus the final screenshot.
- **Self-healing (bonus):** if a step ends blocked, it is retried once with the failure reason added to the prompt
  ("the UI may differ from what you expected"). Healed steps are marked `(self-healed)` in the report. After one
  retry the failure stands, so retries cannot mask real bugs indefinitely.
- Failure reports state expected vs observed, with a quoted piece of evidence so a developer can act on it.

## 5. Trigger

Adding the `RFQA` label to a GitHub issue fires a signed webhook (`agent/triggers/webhook.py`, HMAC-SHA256 verified) or the GitHub
Action. The agent comments the report on the issue and adds `qa-passed`, `qa-failed` or `qa-blocked`.
A label stands in for "moving the card to RFQA" because it works in any repository.

## 6. Known limitations (honest notes)

- LLM behaviour is non-deterministic; temperature 0 reduces but does not remove variance. Run twice before trusting a surprising result.
- Verification relies on the accessibility tree, so purely visual defects (colour, layout) are out of scope.
- Criteria run sequentially in one browser session, so a failed login makes later criteria BLOCKED by design.
- The target is a public demo site; its markup or behaviour may change without notice.
