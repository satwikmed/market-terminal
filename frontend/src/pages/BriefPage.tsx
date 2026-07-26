import { useState } from 'react';
import { api } from '../lib/api';

export function BriefPage() {
  const [brief, setBrief] = useState<string | null>(null);
  const [meta, setMeta] = useState<string>('');
  const [loading, setLoading] = useState(false);

  return (
    <div className="max-w-3xl fade-up">
      <h2 className="text-2xl font-semibold tracking-tight">Weekly State of the Union</h2>
      <p className="text-sm text-terminal-muted mt-2 leading-relaxed">
        One cohesive plain-English narrative for the week — S&P 500 moves, filings/earnings highlights, and Fed/macro context.
        Generated on demand and cached for the week so we don't burn tokens regenerating it.
      </p>
      <button
        type="button"
        disabled={loading}
        onClick={async () => {
          setLoading(true);
          try {
            const r = await api.weeklyBrief();
            setBrief(r.brief);
            setMeta(`Week ${r.week}${r.cached ? ' · cached' : ' · freshly generated'}`);
          } finally {
            setLoading(false);
          }
        }}
        className="mt-6 font-mono text-xs uppercase tracking-wider px-4 py-2 border border-terminal-accent text-terminal-accent hover:bg-terminal-accent/10 disabled:opacity-50"
      >
        {loading ? 'Writing…' : "Generate this week's brief"}
      </button>
      {meta && <p className="mt-3 font-mono text-[11px] text-terminal-muted">{meta}</p>}
      {brief && (
        <article className="mt-6 border border-terminal-border bg-terminal-panel/40 p-6 text-[15px] leading-7 text-terminal-text whitespace-pre-wrap">
          {brief}
        </article>
      )}
    </div>
  );
}
