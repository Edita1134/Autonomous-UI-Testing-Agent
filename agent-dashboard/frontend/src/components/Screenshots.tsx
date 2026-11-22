import { useEffect, useState } from "react";

interface Props {
  urls: string[];
}

/** Thumbnail grid plus a full-screen viewer (click a thumbnail; arrow keys and Esc work). */
export function Screenshots({ urls }: Props) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  useEffect(() => {
    if (openIndex === null) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpenIndex(null);
      if (event.key === "ArrowRight") setOpenIndex((i) => (i === null ? i : Math.min(urls.length - 1, i + 1)));
      if (event.key === "ArrowLeft") setOpenIndex((i) => (i === null ? i : Math.max(0, i - 1)));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openIndex, urls.length]);

  return (
    <section className="card">
      <h2>Screenshots {urls.length > 0 && <span className="count">{urls.length}</span>}</h2>
      {urls.length === 0 && <p className="empty">None yet</p>}
      <div className="shots">
        {urls.map((url, index) => (
          <button key={url} onClick={() => setOpenIndex(index)} aria-label={`Open screenshot ${index + 1}`}>
            <img src={url} alt={`Screenshot ${index + 1}`} loading="lazy" />
          </button>
        ))}
      </div>

      {openIndex !== null && urls[openIndex] && (
        <div className="lightbox" onClick={() => setOpenIndex(null)} role="dialog" aria-modal>
          <img src={urls[openIndex]} alt={`Screenshot ${openIndex + 1}`} />
          <p>
            {openIndex + 1} / {urls.length} · ← → to browse · Esc to close
          </p>
        </div>
      )}
    </section>
  );
}
