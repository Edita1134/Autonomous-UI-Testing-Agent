import { useEffect, useState } from "react";
import { api } from "../api";
import { getTargetUrl, isValidUrl, setTargetUrl } from "../ticketUrl";
import type { Sample } from "../types";

interface Props {
  samples: Sample[];
  markdown: string;
  githubIssue: number | null; // Set while the shown ticket was loaded from this GitHub issue.
  postResult: boolean;
  headed: boolean;
  running: boolean;
  error: string;
  onMarkdownChange: (value: string) => void;
  onGithubLoaded: (issue: number, markdown: string) => void;
  onPostResultChange: (value: boolean) => void;
  onHeadedChange: (value: boolean) => void;
  onRun: () => void;
  onStop: () => void;
}

export function TicketPanel(props: Props) {
  const { samples, markdown, githubIssue, postResult, headed, running, error } = props;
  const [issueInput, setIssueInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");

  const issueNumber = Number.parseInt(issueInput, 10);

  // The website field mirrors the ticket's "Target URL:" line. It keeps its own text so a half-typed address
  // is not lost; the ticket is only rewritten while the address is valid (or cleared).
  const ticketUrl = getTargetUrl(markdown);
  const [urlInput, setUrlInput] = useState(ticketUrl);
  useEffect(() => setUrlInput(ticketUrl), [ticketUrl]);
  const urlIsInvalid = urlInput.trim() !== "" && !isValidUrl(urlInput);

  const changeUrl = (value: string) => {
    setUrlInput(value);
    if (!value.trim() || isValidUrl(value)) props.onMarkdownChange(setTargetUrl(markdown, value));
  };

  const loadFromGithub = async () => {
    setLoading(true);
    setLoadError("");
    try {
      const issue = await api.githubIssue(issueNumber);
      props.onGithubLoaded(issue.number, issue.markdown);
    } catch (failure) {
      setLoadError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card">
      <h2>Ticket · Ready for QA</h2>

      <div className="github-row">
        <input
          type="number"
          min={1}
          aria-label="GitHub issue number"
          placeholder="GitHub issue #"
          value={issueInput}
          disabled={running}
          onChange={(event) => setIssueInput(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && issueNumber > 0 && loadFromGithub()}
        />
        <button className="button secondary" onClick={loadFromGithub} disabled={running || loading || !(issueNumber > 0)}>
          {loading ? "Loading…" : "Load"}
        </button>
      </div>
      {loadError && <div className="error-box">{loadError}</div>}

      <select
        aria-label="Sample ticket"
        disabled={running}
        defaultValue=""
        onChange={(event) => {
          const sample = samples.find((item) => item.name === event.target.value);
          if (sample) props.onMarkdownChange(sample.markdown);
        }}
      >
        <option value="" disabled>
          Or load a sample ticket…
        </option>
        {samples.map((sample) => (
          <option key={sample.name}>{sample.name}</option>
        ))}
      </select>

      <label className="field">
        <span className="field-label">Website to test</span>
        <input
          type="url"
          className="text-input"
          aria-label="Website to test"
          placeholder="https://www.saucedemo.com"
          spellCheck={false}
          value={urlInput}
          disabled={running || githubIssue !== null}
          onChange={(event) => changeUrl(event.target.value)}
        />
      </label>
      {urlIsInvalid ? (
        <p className="field-hint invalid">Enter a full address starting with http:// or https://</p>
      ) : (
        <p className="field-hint">The acceptance criteria below must describe this site. Empty uses the default site.</p>
      )}

      {githubIssue !== null && (
        <p className="note github-note">
          Loaded from GitHub issue #{githubIssue}. The agent fetches the issue again when it runs, so edits here are
          not used. Edit the text to detach it and run your version instead.
        </p>
      )}
      <textarea
        aria-label="Ticket markdown"
        spellCheck={false}
        disabled={running}
        value={markdown}
        placeholder={"# Title\nTarget URL: https://...\n\n## Acceptance Criteria\n- AC1: ..."}
        onChange={(event) => props.onMarkdownChange(event.target.value)}
      />

      {githubIssue !== null && (
        <label className="check">
          <input type="checkbox" checked={postResult} disabled={running} onChange={(e) => props.onPostResultChange(e.target.checked)} />
          Post the result to issue #{githubIssue} (comment + qa-* label)
        </label>
      )}
      <label className="check">
        <input type="checkbox" checked={headed} disabled={running} onChange={(e) => props.onHeadedChange(e.target.checked)} />
        Show the browser window while testing
      </label>
      {running ? (
        <button className="button danger" onClick={props.onStop}>
          Stop run
        </button>
      ) : (
        <button className="button primary" onClick={props.onRun} disabled={!markdown.trim()}>
          {githubIssue !== null ? `Run issue #${githubIssue}` : "Run agent"}
        </button>
      )}
      {error && <div className="error-box">{error}</div>}
    </section>
  );
}
