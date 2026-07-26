import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';
import { api, type LeaderboardRow } from '../lib/api';

type SortKey = 'beta' | 'volatility_pct' | 'max_drawdown_pct' | 'rsi_14' | 'return_window_pct' | 'market_cap';

const SECTOR_COLORS: Record<string, string> = {
  'Information Technology': '#ff6b4a',
  'Health Care': '#2a9d8f',
  Financials: '#e9a820',
  'Consumer Discretionary': '#e76f51',
  'Communication Services': '#457b9d',
  Industrials: '#6a994e',
  'Consumer Staples': '#bc6c25',
  Energy: '#d62828',
  Utilities: '#4a6fa5',
  'Real Estate': '#9b5de5',
  Materials: '#c9a227',
};

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="panel-plain p-4">
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-terminal-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold font-mono tabular-nums text-terminal-text">{value}</div>
      {sub && <div className="mt-1 text-xs text-terminal-muted leading-snug">{sub}</div>}
    </div>
  );
}

export function RiskPage() {
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>('volatility_pct');
  const [asc, setAsc] = useState(false);
  const [corrInput, setCorrInput] = useState('AAPL, MSFT, NVDA, JPM, XOM, JNJ');
  const [corr, setCorr] = useState<{ tickers: string[]; matrix: (number | null)[][]; observations: number } | null>(null);
  const [corrBusy, setCorrBusy] = useState(false);

  useEffect(() => {
    api
      .riskLeaderboard()
      .then((r) => setRows(r.rows))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
    runCorrelation('AAPL, MSFT, NVDA, JPM, XOM, JNJ');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stats = useMemo(() => {
    const withBeta = rows.filter((r) => r.beta != null);
    const avgBeta = withBeta.length ? withBeta.reduce((s, r) => s + (r.beta ?? 0), 0) / withBeta.length : 0;
    const avgVol = rows.length ? rows.reduce((s, r) => s + r.volatility_pct, 0) / rows.length : 0;
    const oversold = rows.filter((r) => r.rsi_14 != null && r.rsi_14 < 30).length;
    const overbought = rows.filter((r) => r.rsi_14 != null && r.rsi_14 > 70).length;
    return { avgBeta, avgVol, oversold, overbought };
  }, [rows]);

  const scatterData = useMemo(
    () =>
      rows
        .filter((r) => r.market_cap && r.volatility_pct != null)
        // Clip a handful of recent-spin-off outliers so the cloud stays legible.
        .filter((r) => r.volatility_pct <= 100 && r.return_window_pct <= 300 && r.return_window_pct >= -100)
        .map((r) => ({
          x: r.volatility_pct,
          y: r.return_window_pct,
          z: r.market_cap ?? 0,
          ticker: r.ticker,
          sector: r.sector,
        })),
    [rows],
  );

  const sorted = useMemo(() => {
    const out = [...rows].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return asc ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
    return out.slice(0, 40);
  }, [rows, sortKey, asc]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) setAsc((v) => !v);
    else {
      setSortKey(key);
      setAsc(false);
    }
  }

  async function runCorrelation(raw: string) {
    const tickers = raw
      .split(',')
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);
    if (tickers.length < 2) return;
    setCorrBusy(true);
    try {
      setCorr(await api.correlation(tickers));
    } catch {
      setCorr(null);
    } finally {
      setCorrBusy(false);
    }
  }

  function corrColor(v: number | null): string {
    if (v == null) return 'transparent';
    // -1 (green, diversifying) → 0 (paper) → +1 (vermillion, moves together)
    if (v >= 0) return `rgba(255, 36, 0, ${0.12 + v * 0.7})`;
    return `rgba(0, 122, 77, ${0.12 + Math.abs(v) * 0.7})`;
  }

  const cols: { key: SortKey; label: string }[] = [
    { key: 'beta', label: 'Beta' },
    { key: 'volatility_pct', label: 'Volatility' },
    { key: 'max_drawdown_pct', label: 'Max DD' },
    { key: 'rsi_14', label: 'RSI(14)' },
    { key: 'return_window_pct', label: '2Y Return' },
  ];

  return (
    <div className="space-y-8 fade-up">
      <div className="border-b-2 border-terminal-text pb-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-terminal-accent mb-2">Quant · risk lab</p>
        <h2 className="brand-mark text-[clamp(2rem,5vw,3.75rem)]">Risk &amp; volatility</h2>
        <p className="text-base text-terminal-muted mt-3 max-w-2xl leading-snug">
          Beta, volatility, drawdown, and correlations computed from two years of daily closes, measured
          against SPY. This is the math desks actually use to size risk — here it&apos;s legible.
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Avg beta vs SPY" value={stats.avgBeta.toFixed(2)} sub="1.0 = moves with the market" />
        <StatCard label="Avg annualized vol" value={`${stats.avgVol.toFixed(1)}%`} sub="Higher = bigger daily swings" />
        <StatCard label="Oversold (RSI<30)" value={String(stats.oversold)} sub="Recently sold off hard" />
        <StatCard label="Overbought (RSI>70)" value={String(stats.overbought)} sub="Recently ran up fast" />
      </div>

      <section className="panel-plain p-4">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
          Risk vs reward · volatility (x) against 2-year return (y)
        </h3>
        <p className="text-xs text-terminal-muted mt-1 mb-3">
          Bubble size = market cap. Bottom-right = high risk, low reward. Top-left = the holy grail.
        </p>
        <div className="h-96">
          {loading ? (
            <div className="h-full grid place-items-center font-mono text-terminal-muted">Computing…</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 10 }}>
                <CartesianGrid stroke="rgba(10,11,14,0.08)" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name="Volatility"
                  unit="%"
                  domain={[0, 100]}
                  tick={{ fill: '#5a6270', fontSize: 10 }}
                  label={{ value: 'Annualized volatility %', position: 'insideBottom', offset: -15, fill: '#5a6270', fontSize: 11 }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name="Return"
                  unit="%"
                  domain={[-100, 300]}
                  tick={{ fill: '#5a6270', fontSize: 10 }}
                  label={{ value: '2Y return %', angle: -90, position: 'insideLeft', fill: '#5a6270', fontSize: 11 }}
                />
                <ZAxis type="number" dataKey="z" range={[20, 400]} />
                <Tooltip
                  cursor={{ strokeDasharray: '3 3' }}
                  content={({ payload }) => {
                    const p = payload?.[0]?.payload as { ticker: string; x: number; y: number; sector: string } | undefined;
                    if (!p) return null;
                    return (
                      <div className="bg-terminal-text text-terminal-panel px-3 py-2 font-mono text-xs">
                        <div className="text-terminal-accent font-semibold">{p.ticker}</div>
                        <div>vol {p.x.toFixed(1)}% · ret {p.y.toFixed(1)}%</div>
                        <div className="opacity-70">{p.sector}</div>
                      </div>
                    );
                  }}
                />
                <Scatter data={scatterData} fillOpacity={0.7}>
                  {scatterData.map((d) => (
                    <Cell key={d.ticker} fill={SECTOR_COLORS[d.sector] ?? '#7a8799'} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="panel-plain p-4">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
            Risk leaderboard · top 40
          </h3>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-terminal-text">
                  <th className="px-2 py-2 text-left font-mono text-[10px] uppercase tracking-wider text-terminal-muted">Ticker</th>
                  {cols.map((c) => (
                    <th
                      key={c.key}
                      onClick={() => toggleSort(c.key)}
                      className={`px-2 py-2 text-right font-mono text-[10px] uppercase tracking-wider cursor-pointer select-none whitespace-nowrap ${
                        sortKey === c.key ? 'text-terminal-accent' : 'text-terminal-muted hover:text-terminal-text'
                      }`}
                    >
                      {c.label}
                      {sortKey === c.key ? (asc ? ' ▲' : ' ▼') : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((r) => (
                  <tr key={r.ticker} className="border-b border-terminal-border/60 hover:bg-terminal-accent/5">
                    <td className="px-2 py-1.5">
                      <Link to={`/company/${r.ticker}`} className="font-mono font-semibold text-terminal-accent hover:underline">
                        {r.ticker}
                      </Link>
                    </td>
                    <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.beta?.toFixed(2) ?? '—'}</td>
                    <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.volatility_pct.toFixed(1)}%</td>
                    <td className="px-2 py-1.5 text-right font-mono tabular-nums text-down">{r.max_drawdown_pct.toFixed(1)}%</td>
                    <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.rsi_14?.toFixed(0) ?? '—'}</td>
                    <td className={`px-2 py-1.5 text-right font-mono tabular-nums ${r.return_window_pct >= 0 ? 'text-up' : 'text-down'}`}>
                      {r.return_window_pct.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel-plain p-4">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
            Correlation heatmap
          </h3>
          <p className="text-xs text-terminal-muted mt-1">
            How tightly names move together. <span className="text-terminal-accent">Red</span> = move as one (no
            diversification); <span className="text-up">green</span> = offsetting.
          </p>
          <div className="mt-3 flex gap-2">
            <input
              value={corrInput}
              onChange={(e) => setCorrInput(e.target.value)}
              className="flex-1 bg-terminal-panel border border-terminal-border px-2 py-1.5 font-mono text-sm outline-none focus:border-terminal-accent"
              placeholder="AAPL, MSFT, NVDA…"
            />
            <button onClick={() => runCorrelation(corrInput)} className="btn-signal" disabled={corrBusy}>
              {corrBusy ? '…' : 'Run'}
            </button>
          </div>
          {corr && corr.tickers.length > 0 && (
            <div className="mt-4 overflow-x-auto">
              <table className="border-collapse font-mono text-[11px]">
                <thead>
                  <tr>
                    <th className="p-1.5"></th>
                    {corr.tickers.map((t) => (
                      <th key={t} className="p-1.5 text-terminal-muted font-semibold">{t}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {corr.matrix.map((row, i) => (
                    <tr key={corr.tickers[i]}>
                      <td className="p-1.5 text-terminal-muted font-semibold text-right">{corr.tickers[i]}</td>
                      {row.map((v, j) => (
                        <td
                          key={j}
                          className="p-1.5 text-center tabular-nums"
                          style={{ background: corrColor(v), color: v != null && Math.abs(v) > 0.6 ? '#fff' : '#0a0b0e' }}
                          title={`${corr.tickers[i]} ↔ ${corr.tickers[j]}: ${v ?? 'n/a'}`}
                        >
                          {v == null ? '—' : v.toFixed(2)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-2 text-[10px] font-mono text-terminal-muted">
                {corr.observations} shared trading days · daily-return correlation
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
