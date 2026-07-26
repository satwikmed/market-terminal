import { useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api, type BacktestResult } from '../lib/api';

type Holding = { ticker: string; weight: number };

const PRESETS: { label: string; holdings: Holding[] }[] = [
  { label: 'Big Tech', holdings: [{ ticker: 'AAPL', weight: 20 }, { ticker: 'MSFT', weight: 20 }, { ticker: 'NVDA', weight: 20 }, { ticker: 'GOOGL', weight: 20 }, { ticker: 'META', weight: 20 }] },
  { label: 'Balanced', holdings: [{ ticker: 'AAPL', weight: 25 }, { ticker: 'JPM', weight: 25 }, { ticker: 'JNJ', weight: 25 }, { ticker: 'XOM', weight: 25 }] },
  { label: 'Defensive', holdings: [{ ticker: 'JNJ', weight: 25 }, { ticker: 'PG', weight: 25 }, { ticker: 'KO', weight: 25 }, { ticker: 'WMT', weight: 25 }] },
];

function Metric({ label, value, tone }: { label: string; value: string; tone?: 'up' | 'down' | 'neutral' }) {
  const color = tone === 'up' ? 'text-up' : tone === 'down' ? 'text-down' : 'text-terminal-text';
  return (
    <div className="panel-plain p-3">
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-terminal-muted">{label}</div>
      <div className={`mt-1 text-xl font-semibold font-mono tabular-nums ${color}`}>{value}</div>
    </div>
  );
}

export function PortfolioPage() {
  const [holdings, setHoldings] = useState<Holding[]>([
    { ticker: 'AAPL', weight: 40 },
    { ticker: 'MSFT', weight: 30 },
    { ticker: 'JPM', weight: 30 },
  ]);
  const [ticker, setTicker] = useState('');
  const [weight, setWeight] = useState(10);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalWeight = holdings.reduce((s, h) => s + h.weight, 0);

  function add() {
    const t = ticker.trim().toUpperCase();
    if (!t || holdings.some((h) => h.ticker === t)) return;
    setHoldings([...holdings, { ticker: t, weight }]);
    setTicker('');
  }

  async function run() {
    if (holdings.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.backtest(holdings));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Backtest failed');
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8 fade-up">
      <div className="border-b-2 border-terminal-text pb-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-terminal-accent mb-2">Portfolio · backtest</p>
        <h2 className="brand-mark text-[clamp(2rem,5vw,3.75rem)]">Build a basket, test it</h2>
        <p className="text-base text-terminal-muted mt-3 max-w-2xl leading-snug">
          Pick names and weights, then replay the last two years against the S&amp;P 500. You get return,
          volatility, Sharpe, drawdown, beta, and each holding&apos;s contribution — a buy-and-hold
          simulation from real daily closes. Educational, not advice.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6">
        <div className="space-y-4">
          <div className="panel-plain p-4">
            <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent mb-3">Holdings</h3>
            <div className="flex gap-2 flex-wrap mb-3">
              {PRESETS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => { setHoldings(p.holdings); setResult(null); }}
                  className="btn-ghost"
                >
                  {p.label}
                </button>
              ))}
            </div>
            <div className="space-y-2">
              {holdings.map((h, i) => (
                <div key={h.ticker} className="flex items-center gap-2">
                  <span className="font-mono font-semibold text-terminal-text w-16">{h.ticker}</span>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={h.weight}
                    onChange={(e) => {
                      const next = [...holdings];
                      next[i] = { ...h, weight: Number(e.target.value) };
                      setHoldings(next);
                    }}
                    className="flex-1 accent-terminal-accent"
                  />
                  <span className="font-mono text-sm tabular-nums w-12 text-right">{h.weight}%</span>
                  <button
                    onClick={() => setHoldings(holdings.filter((x) => x.ticker !== h.ticker))}
                    className="text-terminal-muted hover:text-down font-mono text-sm px-1"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-3 border-t border-terminal-border flex gap-2">
              <input
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && add()}
                placeholder="Add ticker"
                className="flex-1 bg-terminal-panel border border-terminal-border px-2 py-1.5 font-mono text-sm outline-none focus:border-terminal-accent uppercase"
              />
              <input
                type="number"
                value={weight}
                onChange={(e) => setWeight(Number(e.target.value) || 0)}
                className="w-16 bg-terminal-panel border border-terminal-border px-2 py-1.5 font-mono text-sm outline-none focus:border-terminal-accent"
              />
              <button onClick={add} className="btn-ghost">Add</button>
            </div>
            <p className="mt-2 font-mono text-[11px] text-terminal-muted">
              Total weight {totalWeight}% · normalized to 100% on run
            </p>
            <button onClick={run} disabled={busy || holdings.length === 0} className="btn-signal w-full mt-3 disabled:opacity-50">
              {busy ? 'Running backtest…' : 'Run 2-year backtest'}
            </button>
            {error && <p className="mt-2 font-mono text-[11px] text-down">{error}</p>}
          </div>
        </div>

        <div className="space-y-6">
          {!result ? (
            <div className="panel-plain p-10 grid place-items-center text-center">
              <p className="font-mono text-terminal-muted">Set your weights and run a backtest to see the equity curve.</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Metric label="Total return" value={`${result.metrics.total_return_pct}%`} tone={result.metrics.total_return_pct >= 0 ? 'up' : 'down'} />
                <Metric label="vs S&P 500" value={`${result.metrics.excess_return_pct != null && result.metrics.excess_return_pct >= 0 ? '+' : ''}${result.metrics.excess_return_pct}%`} tone={(result.metrics.excess_return_pct ?? 0) >= 0 ? 'up' : 'down'} />
                <Metric label="CAGR" value={`${result.metrics.cagr_pct}%`} />
                <Metric label="Volatility" value={`${result.metrics.annualized_volatility_pct}%`} />
                <Metric label="Sharpe" value={result.metrics.sharpe_ratio?.toFixed(2) ?? '—'} />
                <Metric label="Max drawdown" value={`${result.metrics.max_drawdown_pct}%`} tone="down" />
                <Metric label="Beta vs SPY" value={result.metrics.beta_vs_spy?.toFixed(2) ?? '—'} />
                <Metric label="S&P return" value={`${result.metrics.benchmark_total_return_pct}%`} />
              </div>

              <section className="panel-plain p-4">
                <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
                  Growth of $1 · portfolio vs S&amp;P 500
                </h3>
                <p className="text-xs text-terminal-muted mt-1 mb-3">
                  {result.start_date} → {result.end_date} · {result.trading_days} trading days
                </p>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={result.curve}>
                      <CartesianGrid stroke="rgba(10,11,14,0.08)" />
                      <XAxis dataKey="date" tick={{ fill: '#5a6270', fontSize: 10 }} minTickGap={50} />
                      <YAxis tick={{ fill: '#5a6270', fontSize: 10 }} width={44} domain={['auto', 'auto']} tickFormatter={(v) => `$${v.toFixed(1)}`} />
                      <Tooltip
                        contentStyle={{ background: '#0a0b0e', border: 'none', color: '#f3f4f8', fontFamily: 'JetBrains Mono', fontSize: 12 }}
                        formatter={(value, name) => [`$${Number(value).toFixed(3)}`, name === 'portfolio' ? 'Portfolio' : 'S&P 500']}
                      />
                      <Line type="monotone" dataKey="benchmark" stroke="#5a6270" dot={false} strokeWidth={1.4} strokeDasharray="4 3" />
                      <Line type="monotone" dataKey="portfolio" stroke="#ff2400" dot={false} strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </section>

              <section className="panel-plain p-4">
                <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent mb-3">
                  Return contribution
                </h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-terminal-text text-terminal-muted font-mono text-[10px] uppercase tracking-wider">
                      <th className="px-2 py-2 text-left">Ticker</th>
                      <th className="px-2 py-2 text-right">Weight</th>
                      <th className="px-2 py-2 text-right">Return</th>
                      <th className="px-2 py-2 text-right">Contribution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.contributions.map((c) => (
                      <tr key={c.ticker} className="border-b border-terminal-border/60">
                        <td className="px-2 py-1.5 font-mono font-semibold">{c.ticker}</td>
                        <td className="px-2 py-1.5 text-right font-mono tabular-nums">{c.weight_pct}%</td>
                        <td className={`px-2 py-1.5 text-right font-mono tabular-nums ${c.return_pct >= 0 ? 'text-up' : 'text-down'}`}>{c.return_pct}%</td>
                        <td className={`px-2 py-1.5 text-right font-mono tabular-nums ${c.contribution_pct >= 0 ? 'text-up' : 'text-down'}`}>{c.contribution_pct}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-3 font-mono text-[10px] text-terminal-muted">{result.note}</p>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
