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
    <div className="absolute inset-0 overflow-hidden">
      {/* Full-bleed map — the dominant visual plane */}
      <div className="absolute inset-0 map-bloom">
        {loading ? (
          <div className="h-full grid place-items-center font-mono text-terminal-muted">
            Loading the S&amp;P 500…
          </div>
        ) : error ? (
          <div className="h-full grid place-items-center text-down p-8 text-center">
            <div>
              <p className="font-mono font-semibold">Backend unreachable</p>
              <p className="text-sm text-terminal-muted mt-2">Start the API on :8000: {error}</p>
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
            bare
          />
        )}
      </div>

      {/* Brand + controls overlay — one composition, not a dashboard chrome */}
      <div className="pointer-events-none absolute inset-0 z-20 flex flex-col justify-between p-4 md:p-6 lg:p-8">
        <div className="pointer-events-auto max-w-3xl stamp-in">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-terminal-accent mb-3">
            S&amp;P 500 · live map
          </p>
          <h1 className="brand-mark text-[clamp(2.75rem,9vw,7.5rem)] text-terminal-text">
            Lumen
            <span className="text-terminal-accent">.</span>
          </h1>
          <p className="mt-4 max-w-md text-base md:text-lg text-terminal-muted leading-snug">
            Every company as a bubble. Size is market cap. Color is today’s move. Click anything: we’ll explain it in English.
          </p>
          <div className="signal-rule w-16 mt-5" />
        </div>

        <div className="pointer-events-auto flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="flex flex-wrap gap-2 fade-up" style={{ animationDelay: '120ms' }}>
            {(
              [
                ['industry', 'By industry'],
                ['relationships', 'Relationships'],
                ['rate', 'Rate sensitivity'],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setMode(id)}
                className={`btn-ghost ${mode === id ? 'is-active' : ''}`}
              >
                {label}
              </button>
            ))}
          </div>

          <div
            className="w-full lg:w-[320px] panel-plain p-3 backdrop-blur-md fade-up"
            style={{ animationDelay: '200ms' }}
          >
            <label className="block font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-muted">
              Jump to a company
            </label>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="AAPL, Microsoft…"
              className="mt-2 w-full bg-transparent border-b border-terminal-border px-0 py-2 font-mono text-sm outline-none focus:border-terminal-accent placeholder:text-terminal-muted"
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

            <div className="mt-3 pt-3 border-t border-terminal-border">
              {mode === 'industry' && (
                <p className="text-xs text-terminal-muted leading-relaxed">
                  Green rises, red falls. Clusters are sectors sitting near each other.
                </p>
              )}
              {mode === 'rate' && (
                <p className="text-xs text-terminal-muted leading-relaxed">
                  Redder = historically weakened when rates rose. Tendency, not a forecast.
                </p>
              )}
              {mode === 'relationships' && (
                <div className="max-h-36 overflow-auto space-y-2">
                  {!focus && (
                    <p className="text-xs text-terminal-muted">Click a bubble to map its network.</p>
                  )}
                  {focus && rels.length === 0 && (
                    <p className="text-xs text-terminal-muted">Loading {focus}…</p>
                  )}
                  {rels.slice(0, 6).map((r) => (
                    <div key={r.target_ticker} className="text-xs">
                      <button
                        type="button"
                        className="font-mono text-terminal-accent hover:underline"
                        onClick={() => setFocus(r.target_ticker)}
                      >
                        {r.target_ticker}
                      </button>
                      <Link
                        to={`/company/${r.target_ticker}`}
                        className="ml-2 text-terminal-muted hover:text-terminal-text"
                      >
                        open
                      </Link>
                      <span className="ml-2 font-mono text-[9px] uppercase text-terminal-warn">
                        {r.relationship_type}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
