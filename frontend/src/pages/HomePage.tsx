import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { BubbleMap } from '../components/BubbleMap';
import { api, type BubbleNode, type Relationship } from '../lib/api';

type Mode = 'industry' | 'relationships' | 'rate';

export function HomePage() {
  const [nodes, setNodes] = useState<BubbleNode[]>([]);
  const [mode, setMode] = useState<Mode>('industry');
  const [focus, setFocus] = useState<string | null>('AAPL');
  const [rels, setRels] = useState<Relationship[]>([]);
  const [rateSensitivity, setRateSensitivity] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [bubble, rates] = await Promise.all([api.bubble(), api.rateSensitivity()]);
        if (!alive) return;
        setNodes(bubble.nodes);
        setRateSensitivity(rates.sectors);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load map');
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!focus || mode !== 'relationships') return;
    api.relationships(focus).then(setRels).catch(() => setRels([]));
  }, [focus, mode]);

  const related = useMemo(() => new Set(rels.map((r) => r.target_ticker)), [rels]);

  const filteredHint = useMemo(() => {
    if (!query.trim()) return null;
    const q = query.trim().toUpperCase();
    return nodes.find((n) => n.ticker === q || n.name.toUpperCase().includes(q));
  }, [query, nodes]);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-4 h-[calc(100vh-210px)] min-h-[600px]">
      <section className="border border-terminal-border bg-terminal-panel/40 overflow-hidden flex flex-col fade-up">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-terminal-border">
          <div>
            <h2 className="text-lg font-semibold tracking-tight">Industry Bubble Map</h2>
            <p className="text-sm text-terminal-muted">
              All {nodes.length || '500'} S&P 500 companies — size is market cap, clustered by sector.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 font-mono text-[11px] uppercase tracking-wider">
            {(
              [
                ['industry', 'By Industry'],
                ['relationships', 'Relationships'],
                ['rate', 'Rate Sensitivity'],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setMode(id)}
                className={`px-3 py-1.5 border transition-colors ${
                  mode === id
                    ? 'border-terminal-accent text-terminal-accent'
                    : 'border-terminal-border text-terminal-muted hover:text-terminal-text'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        {loading ? (
          <div className="flex-1 grid place-items-center font-mono text-terminal-muted">Loading universe…</div>
        ) : error ? (
          <div className="flex-1 grid place-items-center text-down p-8 text-center">
            <div>
              <p className="font-mono">Backend unreachable</p>
              <p className="text-sm text-terminal-muted mt-2">Start the API on :8000 — {error}</p>
            </div>
          </div>
        ) : (
          <BubbleMap
            nodes={nodes}
            mode={mode}
            focusTicker={focus}
            relatedTickers={related}
            rateSensitivity={rateSensitivity}
            onSelect={setFocus}
          />
        )}
      </section>

      <aside className="border border-terminal-border bg-terminal-panel/40 p-4 overflow-auto fade-up" style={{ animationDelay: '80ms' }}>
        <label className="block font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-muted">Find ticker</label>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="AAPL, Microsoft…"
          className="mt-2 w-full bg-terminal-bg border border-terminal-border px-3 py-2 font-mono text-sm outline-none focus:border-terminal-accent"
        />
        {filteredHint && (
          <button
            type="button"
            className="mt-2 text-left w-full text-sm text-terminal-accent hover:underline font-mono"
            onClick={() => {
              setFocus(filteredHint.ticker);
              setMode('relationships');
            }}
          >
            Focus {filteredHint.ticker} · {filteredHint.name}
          </button>
        )}

        <div className="mt-6">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
            {mode === 'relationships' ? `Links · ${focus ?? '—'}` : mode === 'rate' ? 'Fed rate overlay' : 'How to read this'}
          </h3>
          {mode === 'industry' && (
            <p className="mt-2 text-sm text-terminal-muted leading-relaxed">
              Bigger bubbles = bigger companies. Green/red = today's move. Clusters sit near their industry peers so you can see which corners of the market are winning or losing together.
            </p>
          )}
          {mode === 'rate' && (
            <p className="mt-2 text-sm text-terminal-muted leading-relaxed">
              Color encodes historical sensitivity to rising rates (redder = tended to weaken). Real estate, banks, and growth tech often react most — a historical tendency, not a prediction.
            </p>
          )}
          {mode === 'relationships' && (
            <ul className="mt-3 space-y-3">
              {!focus && (
                <li className="text-sm text-terminal-muted">
                  Click any bubble — every S&P 500 company now has mapped connections (industry peers plus curated supplier/customer/partner links).
                </li>
              )}
              {focus && rels.length === 0 && (
                <li className="text-sm text-terminal-muted">Loading connections for {focus}…</li>
              )}
              {rels.map((r) => (
                <li key={r.target_ticker} className="border-b border-terminal-border/70 pb-3">
                  <button
                    type="button"
                    className="font-mono text-sm text-terminal-accent hover:underline"
                    onClick={() => setFocus(r.target_ticker)}
                  >
                    {r.target_ticker}
                  </button>
                  <Link to={`/company/${r.target_ticker}`} className="ml-2 text-[10px] text-terminal-muted hover:text-terminal-text">
                    open
                  </Link>
                  <span className="ml-2 text-[10px] uppercase tracking-wider text-terminal-warn font-mono">
                    {r.relationship_type}
                  </span>
                  <p className="text-sm text-terminal-muted mt-1 leading-snug">{r.plain_english}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </div>
  );
}
