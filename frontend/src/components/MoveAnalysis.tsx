import { useEffect, useState } from 'react';
import { api, formatPct, type WhyMove } from '../lib/api';

const KIND_LABEL: Record<string, string> = {
  market: 'Market',
  sector: 'Industry',
  volatility: 'Context',
  filing: 'SEC filing',
  macro: 'Economy',
};

type Props = { ticker: string };

/**
 * Shows the move decomposition and the evidence behind it. The evidence loads
 * automatically because it is computed locally and costs nothing; the AI
 * narrative is opt-in.
 */
export function MoveAnalysis({ ticker }: Props) {
  const [data, setData] = useState<WhyMove | null>(null);
  const [aiNarrative, setAiNarrative] = useState<WhyMove | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    setData(null);
    setAiNarrative(null);
    api
      .moveEvidence(ticker)
      .then((r) => alive && setData(r))
      .catch(() => alive && setData(null));
    return () => {
      alive = false;
    };
  }, [ticker]);

  if (!data) {
    return (
      <section className="panel-plain p-4">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
          Why did this move?
        </h3>
        <p className="mt-3 text-sm text-terminal-muted">Gathering evidence…</p>
      </section>
    );
  }

  const attribution = data.attribution;
  const shown = aiNarrative ?? data;

  return (
    <section className="panel-plain p-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
          Why did this move?
        </h3>
        <span className="font-mono text-[10px] text-terminal-muted">
          {formatPct(data.change_pct)} today
        </span>
      </div>

      {attribution && (
        <div className="mt-3">
          <div className="flex h-6 w-full overflow-hidden border border-terminal-border font-mono text-[9px]">
            <div
              className="bg-[#c5c9d2] grid place-items-center text-terminal-text"
              style={{ width: `${attribution.shares.market}%` }}
              title={`Market: ${attribution.market_pct.toFixed(2)}%`}
            >
              {attribution.shares.market >= 12 ? `MKT ${attribution.shares.market}%` : ''}
            </div>
            <div
              className="bg-[#e9a820] grid place-items-center text-terminal-text"
              style={{ width: `${attribution.shares.sector}%` }}
              title={`Industry: ${attribution.sector_excess_pct.toFixed(2)}%`}
            >
              {attribution.shares.sector >= 12 ? `IND ${attribution.shares.sector}%` : ''}
            </div>
            <div
              className="bg-terminal-accent grid place-items-center text-white"
              style={{ width: `${attribution.shares.company}%` }}
              title={`Company specific: ${attribution.company_specific_pct.toFixed(2)}%`}
            >
              {attribution.shares.company >= 12 ? `CO ${attribution.shares.company}%` : ''}
            </div>
          </div>
          <p className="mt-2 text-sm">{attribution.plain_english}</p>
          <details className="mt-1">
            <summary className="font-mono text-[10px] uppercase tracking-wider text-terminal-muted cursor-pointer hover:text-terminal-accent">
              How this is calculated
            </summary>
            <p className="mt-1 text-xs text-terminal-muted leading-relaxed">{attribution.method}</p>
          </details>
        </div>
      )}

      <p className="mt-3 text-sm leading-relaxed">{shown.narrative}</p>

      {shown.narrative_source === 'ai' && (
        <p className="mt-1 font-mono text-[10px] text-terminal-muted">
          Written by {shown.provider} from the evidence below: it was not allowed to add anything else.
        </p>
      )}

      <button
        type="button"
        disabled={busy || aiNarrative !== null}
        onClick={async () => {
          setBusy(true);
          try {
            const r = await api.whyMove(ticker);
            setAiNarrative(r);
          } finally {
            setBusy(false);
          }
        }}
        className="mt-3 px-3 py-2 border border-terminal-border hover:border-terminal-accent font-mono text-xs uppercase tracking-wider disabled:opacity-50"
      >
        {busy ? 'Thinking…' : aiNarrative ? 'AI summary loaded' : 'Rewrite this with AI'}
      </button>

      <div className="mt-4 border-t border-terminal-border pt-3">
        <div className="font-mono text-[10px] uppercase tracking-wider text-terminal-muted">
          Evidence ({data.evidence.length})
        </div>
        <ul className="mt-2 space-y-3">
          {data.evidence.length === 0 && (
            <li className="text-sm text-terminal-muted">
              No evidence could be gathered for this move.
            </li>
          )}
          {data.evidence.map((e) => (
            <li key={e.title}>
              <div className="flex items-baseline gap-2 flex-wrap">
                <span className="font-mono text-[9px] uppercase tracking-wider px-1.5 py-0.5 border border-terminal-border text-terminal-warn">
                  {KIND_LABEL[e.kind] ?? e.kind}
                </span>
                <span className="text-sm">{e.title}</span>
              </div>
              <p className="text-sm text-terminal-muted mt-1 leading-relaxed">{e.detail}</p>
              <div className="mt-1 font-mono text-[10px] text-terminal-muted">
                {e.source_url ? (
                  <a href={e.source_url} target="_blank" rel="noreferrer" className="text-terminal-accent hover:underline">
                    {e.source} ↗
                  </a>
                ) : (
                  e.source
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
