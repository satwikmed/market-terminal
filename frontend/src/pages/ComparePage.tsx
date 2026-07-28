import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, formatMoney, type CompanyDetail, type Financials, type RiskMetrics } from '../lib/api';

type Col = {
  ticker: string;
  company?: CompanyDetail;
  financials?: Financials | null;
  risk?: RiskMetrics | null;
  error?: boolean;
};

type RowDef = {
  label: string;
  get: (c: Col) => string;
  group?: boolean;
  better?: 'high' | 'low';
  raw?: (c: Col) => number | null;
};

function pct(v: number | null | undefined): string {
  return v == null ? 'n/a' : `${v.toFixed(1)}%`;
}
function num(v: number | null | undefined, d = 2): string {
  return v == null ? 'n/a' : v.toFixed(d);
}

const ROWS: RowDef[] = [
  { label: 'Valuation', get: () => '', group: true },
  { label: 'Price', get: (c) => (c.company?.price != null ? `$${c.company.price.toFixed(2)}` : 'n/a') },
  { label: 'Market cap', get: (c) => formatMoney(c.company?.market_cap), raw: (c) => c.company?.market_cap ?? null, better: 'high' },
  { label: 'P/E ratio', get: (c) => num(c.company?.pe_ratio), raw: (c) => c.company?.pe_ratio ?? null, better: 'low' },
  { label: 'EPS (TTM)', get: (c) => (c.company?.eps != null ? `$${c.company.eps.toFixed(2)}` : 'n/a') },
  { label: 'Dividend yield', get: (c) => (c.company?.dividend_yield != null ? `${(c.company.dividend_yield * 100).toFixed(2)}%` : 'n/a') },

  { label: 'Profitability (latest FY)', get: () => '', group: true },
  { label: 'Revenue', get: (c) => formatMoney(lastVal(c.financials?.statements.income.revenue)), raw: (c) => lastVal(c.financials?.statements.income.revenue), better: 'high' },
  { label: 'Gross margin', get: (c) => pct(c.financials?.ratios.gross_margin), raw: (c) => c.financials?.ratios.gross_margin ?? null, better: 'high' },
  { label: 'Operating margin', get: (c) => pct(c.financials?.ratios.operating_margin), raw: (c) => c.financials?.ratios.operating_margin ?? null, better: 'high' },
  { label: 'Net margin', get: (c) => pct(c.financials?.ratios.net_margin), raw: (c) => c.financials?.ratios.net_margin ?? null, better: 'high' },
  { label: 'ROE', get: (c) => pct(c.financials?.ratios.roe), raw: (c) => c.financials?.ratios.roe ?? null, better: 'high' },
  { label: 'FCF margin', get: (c) => pct(c.financials?.ratios.fcf_margin), raw: (c) => c.financials?.ratios.fcf_margin ?? null, better: 'high' },
  { label: 'Revenue CAGR', get: (c) => pct(c.financials?.ratios.revenue_cagr), raw: (c) => c.financials?.ratios.revenue_cagr ?? null, better: 'high' },
  { label: 'Debt / equity', get: (c) => num(c.financials?.ratios.debt_to_equity), raw: (c) => c.financials?.ratios.debt_to_equity ?? null, better: 'low' },

  { label: 'Risk (2 year)', get: () => '', group: true },
  { label: 'Beta vs SPY', get: (c) => num(c.risk?.beta), raw: (c) => c.risk?.beta ?? null, better: 'low' },
  { label: 'Volatility', get: (c) => pct(c.risk?.annualized_volatility_pct), raw: (c) => c.risk?.annualized_volatility_pct ?? null, better: 'low' },
  { label: 'Sharpe ratio', get: (c) => num(c.risk?.sharpe_ratio), raw: (c) => c.risk?.sharpe_ratio ?? null, better: 'high' },
  { label: 'Max drawdown', get: (c) => pct(c.risk?.max_drawdown_pct), raw: (c) => c.risk?.max_drawdown_pct ?? null, better: 'high' },
  { label: '2Y return', get: (c) => pct(c.risk?.annualized_return_pct), raw: (c) => c.risk?.annualized_return_pct ?? null, better: 'high' },
  { label: 'RSI(14)', get: (c) => num(c.risk?.rsi_14, 0) },
];

function lastVal(arr?: (number | null)[]): number | null {
  if (!arr) return null;
  for (let i = arr.length - 1; i >= 0; i--) if (arr[i] != null) return arr[i];
  return null;
}

export function ComparePage() {
  const [params, setParams] = useSearchParams();
  const initial = (params.get('tickers') || 'AAPL,MSFT,NVDA').split(',').map((t) => t.trim().toUpperCase()).filter(Boolean);
  const [tickers, setTickers] = useState<string[]>(initial);
  const [input, setInput] = useState('');
  const [cols, setCols] = useState<Col[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    (async () => {
      const results = await Promise.all(
        tickers.slice(0, 4).map(async (t): Promise<Col> => {
          try {
            const [company, financials, risk] = await Promise.all([
              api.company(t),
              api.fundamentals(t).catch(() => null),
              api.risk(t).catch(() => null),
            ]);
            return { ticker: t, company, financials, risk };
          } catch {
            return { ticker: t, error: true };
          }
        }),
      );
      if (alive) {
        setCols(results);
        setLoading(false);
      }
    })();
    setParams({ tickers: tickers.join(',') }, { replace: true });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tickers]);

  function add() {
    const t = input.trim().toUpperCase();
    if (!t || tickers.includes(t) || tickers.length >= 4) return;
    setTickers([...tickers, t]);
    setInput('');
  }

  function bestIndex(row: RowDef): number | null {
    if (!row.raw || !row.better) return null;
    let best: number | null = null;
    let bestVal: number | null = null;
    cols.forEach((c, i) => {
      const v = row.raw!(c);
      if (v == null) return;
      if (bestVal == null || (row.better === 'high' ? v > bestVal : v < bestVal)) {
        bestVal = v;
        best = i;
      }
    });
    return best;
  }

  return (
    <div className="space-y-6 fade-up">
      <div className="border-b-2 border-terminal-text pb-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-terminal-accent mb-2">Compare</p>
        <h2 className="brand-mark text-[clamp(2rem,5vw,3.5rem)]">Head to head</h2>
        <p className="text-base text-terminal-muted mt-3 max-w-2xl leading-snug">
          Up to four names side by side across valuation, profitability from SEC filings, and 2 year risk.
          The <span className="text-terminal-accent">highlighted</span> cell wins each row.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {tickers.map((t) => (
          <span key={t} className="inline-flex items-center gap-2 border border-terminal-border bg-terminal-panel px-3 py-1.5 font-mono text-sm">
            {t}
            <button onClick={() => setTickers(tickers.filter((x) => x !== t))} className="text-terminal-muted hover:text-down">✕</button>
          </span>
        ))}
        {tickers.length < 4 && (
          <span className="inline-flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && add()}
              placeholder="Add ticker"
              className="w-32 bg-terminal-panel border border-terminal-border px-2 py-1.5 font-mono text-sm outline-none focus:border-terminal-accent uppercase"
            />
            <button onClick={add} className="btn-ghost">Add</button>
          </span>
        )}
      </div>

      <div className="panel-plain overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-terminal-text">
              <th className="px-3 py-3 text-left font-mono text-[10px] uppercase tracking-wider text-terminal-muted w-48">Metric</th>
              {cols.map((c) => (
                <th key={c.ticker} className="px-3 py-3 text-right">
                  <div className="font-mono font-bold text-terminal-accent text-base">{c.ticker}</div>
                  <div className="text-[10px] text-terminal-muted font-normal truncate max-w-[140px] ml-auto">
                    {c.company?.name ?? (c.error ? 'not found' : '…')}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => {
              if (row.group) {
                return (
                  <tr key={row.label} className="bg-terminal-text">
                    <td colSpan={cols.length + 1} className="px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-panel">
                      {row.label}
                    </td>
                  </tr>
                );
              }
              const best = bestIndex(row);
              return (
                <tr key={row.label} className="border-b border-terminal-border/60">
                  <td className="px-3 py-2 text-terminal-muted">{row.label}</td>
                  {cols.map((c, i) => (
                    <td
                      key={c.ticker}
                      className={`px-3 py-2 text-right font-mono tabular-nums ${
                        best === i ? 'text-terminal-accent font-semibold bg-terminal-accent/8' : 'text-terminal-text'
                      }`}
                    >
                      {loading && !c.company ? '…' : row.get(c)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="font-mono text-[11px] text-terminal-muted">
        Fundamentals from SEC EDGAR XBRL · risk computed from 2 years of daily closes vs SPY · educational, not advice.
      </p>
    </div>
  );
}
