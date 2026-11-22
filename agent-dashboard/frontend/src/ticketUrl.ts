// The website a ticket tests is its "Target URL:" line. These helpers read and rewrite that one line, so the UI
// can offer it as its own field while the ticket text stays the single source of truth.

const URL_LINE = /^[ \t]*target url:[ \t]*<?(https?:\/\/[^\s>]+)>?[ \t]*$/im;
const ANY_URL_LINE = /^[ \t]*target url:.*$/im;
const URL_LINE_WITH_BREAK = /^[ \t]*target url:.*(?:\r?\n)?/im;

export function isValidUrl(value: string): boolean {
  return /^https?:\/\/\S+$/i.test(value.trim());
}

/** The ticket's target URL, or "" when it has none. */
export function getTargetUrl(markdown: string): string {
  return markdown.match(URL_LINE)?.[1] ?? "";
}

/** The ticket with its Target URL line set to `url` (added under the title if missing, removed if `url` is empty). */
export function setTargetUrl(markdown: string, url: string): string {
  const value = url.trim();
  if (ANY_URL_LINE.test(markdown)) {
    return value ? markdown.replace(ANY_URL_LINE, () => `Target URL: ${value}`) : markdown.replace(URL_LINE_WITH_BREAK, "");
  }
  if (!value) return markdown;
  if (!markdown.trim()) return `# Ticket\nTarget URL: ${value}\n\n## Acceptance Criteria\n- AC1: `;
  const [title, ...rest] = markdown.split("\n");
  return [title, `Target URL: ${value}`, ...rest].join("\n");
}
