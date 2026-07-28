import { useState } from 'react';
import { api } from '../lib/api';

export function BriefPage() {
  const [brief, setBrief] = useState<string | null>(null);
  const [meta, setMeta] = useState<string>('');
  const [loading, setLoading] = useState(false);

  return (
    <div className="max-w-3xl fade-up">
      <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-terminal-accent mb-2">Weekly brief</p>
      <h2 className="brand-mark text-[clamp(2rem,5vw,3.5rem)]">State of the Union</h2>
      <p className="text-base text-terminal-muted mt-3 leading-snug max-w-xl">
        One plain English narrative for the week: market moves, filings, and the Fed. Generated on demand and cached
        so we don&apos;t burn tokens regenerating it.
      </p>
      <div className="signal-rule w-14 mt-5" />
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
        className="btn-signal mt-6 disabled:opacity-50"
      >
        {loading ? 'Writing…' : "Generate this week's brief"}
      </button>
      {meta && <p className="mt-3 font-mono text-[11px] text-terminal-muted">{meta}</p>}
      {brief && (
        <article className="mt-8 border-l-4 border-terminal-accent bg-terminal-panel pl-6 pr-4 py-5 text-[16px] leading-8 text-terminal-text whitespace-pre-wrap">
          {brief}
        </article>
      )}
    </div>
  );
}
