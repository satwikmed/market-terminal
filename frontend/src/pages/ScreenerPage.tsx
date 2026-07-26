import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, formatMoney, type ScreenerRow } from '../lib/api';

type SortKey =
  | 'market_cap'
  | 'pe_ratio'
  | 'dividend_yield_pct'
  | 'change_pct'
  | 'mom_1m_pct'
  | 'mom_3m_pct'
  | 'mom_6m_pct'
  | 'ticker';

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: 'ticker', label: 'Ticker', numeric: false },
  { key: 'market_cap', label: 'Mkt Cap', numeric: true },
  { key: 'pe_ratio', label: 'P/E', numeric: true },
  { key: 'dividend_yield_pct', label: 'Div %', numeric: true },
  { key: 'change_pct', label: 'Day %', numeric: true },
  { key: 'mom_1m_pct', label: '1M %', numeric: true },
  { key: 'mom_3m_pct', label: '3M %', numeric: true },
  { key: 'mom_6m_pct', label: '6M %', numeric: true },
];

function num(v: number | null | undefined): string {
  return v == null ? '—' : v.toFixed(2);
}

function pctClass(v: number | null | undefined): string {
  if (v == null) return 'text-terminal-muted';
  return v >= 0 ? 'text-up' : 'text-down';
}

export function ScreenerPage() {
  const [rows, setRows] = useState<ScreenerRow[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [sector, setSector] = useState<string>('All');
  const [query, setQuery] = useState('');
  const [minCap, setMinCap] = useState(0);
  const [maxPe, setMaxPe] = useState<number | ''>('');
  const [minYield, setMinYield] = useState<number | ''>('');
  const [sortKey, setSortKey] = useState<SortKey>('market_cap');
  const [asc, setAsc] = useState(false);

  useEffect(() => {
    api
      .screener()
      .then((r) => {
        setRows(r.rows);
        setSectors(r.sectors);
      })
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toUpperCase();
    let out = rows.filter((r) => {
      if (sector !== 'All' && r.sector !== sector) return false;
      if (q && !r.ticker.includes(q) && !r.name.toUpperCase().includes(q)) return false;
      if (minCap && (r.market_cap ?? 0) < minCap * 1e9) return false;
      if (maxPe !== '' && (r.pe_ratio == null || r.pe_ratio > maxPe)) return false;
      if (minYield !== '' && (r.dividend_yield_pct ?? 0) < minYield) return false;
      return true;
    });
    out = [...out].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === 'string' || typeof bv === 'string') {
        return asc ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
      }
      return asc ? av - bv : bv - av;
    });
    return out;
  }, [rows, sector, query, minCap, maxPe, minYield, sortKey, asc]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) setAsc((v) => !v);
    else {
      setSortKey(key);
      setAsc(false);
    }
  }

  return (
    <div className="space-y-6 fade-up">
      <div className="border-b-2 border-terminal-text pb-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-terminal-accent mb-2">Screener</p>
        <h2 className="brand-mark text-[clamp(2rem,5vw,3.5rem)]">Filter all 503 names</h2>
        <p className="text-base text-terminal-muted mt-3 max-w-2xl leading-snug">
          Live fundamentals joined with momentum computed from two years of daily bars. Sort any column;
          stack filters. Everything here is a real number — blanks mean the source didn&apos;t report it.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <label className="col-span-2 md:col-span-1">
          <span className="block font-mono text-[10px] uppercase tracking-wider text-terminal-muted mb-1">Search</span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="AAPL, Apple…"
            className="w-full bg-terminal-panel border border-terminal-border px-2 py-1.5 font-mono text-sm outline-none focus:border-terminal-accent"
          />
        </label>
        <label>
          <span className="block font-mono text-[10px] uppercase tracking-wider text-terminal-muted mb-1">Sector</span>
          <select
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            className="w-full bg-terminal-panel border border-terminal-border px-2 py-1.5 font-mono text-sm outline-none focus:border-terminal-accent"
          >
            <option>All</option>
            {sectors.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          <span className="block font-mono text-[10px] uppercase tracking-wider text-terminal-muted mb-1">Min cap ($B)</span>
          <input
            type="number"
            value={minCap || ''}
            onChange={(e) => setMinCap(Number(e.target.value) || 0)}
            placeholder="0"
            className="w-full bg-terminal-panel border border-terminal-border px-2 py-1.5 font-mono text-sm outline-none focus:border-terminal-accent"
          />
        </label>
        <label>
          <span className="block font-mono text-[10px] uppercase tracking-wider text-terminal-muted mb-1">Max P/E</span>
          <input
            type="number"
            value={maxPe}
            onChange={(e) => setMaxPe(e.target.value === '' ? '' : Number(e.target.value))}
            placeholder="any"
            className="w-full bg-terminal-panel border border-terminal-border px-2 py-1.5 font-mono text-sm outline-none focus:border-terminal-accent"
          />
        </label>
        <label>
          <span className="block font-mono text-[10px] uppercase tracking-wider text-terminal-muted mb-1">Min yield %</span>
          <input
            type="number"
            value={minYield}
            onChange={(e) => setMinYield(e.target.value === '' ? '' : Number(e.target.value))}
            placeholder="any"
            className="w-full bg-terminal-panel border border-terminal-border px-2 py-1.5 font-mono text-sm outline-none focus:border-terminal-accent"
          />
        </label>
      </div>

      <div className="flex items-center justify-between font-mono text-[11px] text-terminal-muted">
        <span>
          {loading ? 'Loading…' : `${filtered.length} of ${rows.length} names`}
        </span>
        <span>Click a header to sort · click a row to open</span>
      </div>

      <div className="panel-plain overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-terminal-text">
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  onClick={() => toggleSort(c.key)}
                  className={`px-3 py-2 font-mono text-[10px] uppercase tracking-wider cursor-pointer select-none whitespace-nowrap ${
                    c.numeric ? 'text-right' : 'text-left'
                  } ${sortKey === c.key ? 'text-terminal-accent' : 'text-terminal-muted hover:text-terminal-text'}`}
                >
                  {c.label}
                  {sortKey === c.key ? (asc ? ' ▲' : ' ▼') : ''}
                </th>
              ))}
              <th className="px-3 py-2 text-left font-mono text-[10px] uppercase tracking-wider text-terminal-muted">Sector</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 120).map((r) => (
              <tr key={r.ticker} className="border-b border-terminal-border/60 hover:bg-terminal-accent/5">
                <td className="px-3 py-1.5">
                  <Link to={`/company/${r.ticker}`} className="font-mono font-semibold text-terminal-accent hover:underline">
                    {r.ticker}
                  </Link>
                  <span className="ml-2 text-terminal-muted text-xs hidden lg:inline">{r.name}</span>
                </td>
                <td className="px-3 py-1.5 text-right font-mono tabular-nums">{formatMoney(r.market_cap)}</td>
                <td className="px-3 py-1.5 text-right font-mono tabular-nums">{num(r.pe_ratio)}</td>
                <td className="px-3 py-1.5 text-right font-mono tabular-nums">{num(r.dividend_yield_pct)}</td>
                <td className={`px-3 py-1.5 text-right font-mono tabular-nums ${pctClass(r.change_pct)}`}>{num(r.change_pct)}</td>
                <td className={`px-3 py-1.5 text-right font-mono tabular-nums ${pctClass(r.mom_1m_pct)}`}>{num(r.mom_1m_pct)}</td>
                <td className={`px-3 py-1.5 text-right font-mono tabular-nums ${pctClass(r.mom_3m_pct)}`}>{num(r.mom_3m_pct)}</td>
                <td className={`px-3 py-1.5 text-right font-mono tabular-nums ${pctClass(r.mom_6m_pct)}`}>{num(r.mom_6m_pct)}</td>
                <td className="px-3 py-1.5 text-terminal-muted text-xs whitespace-nowrap">{r.sector}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length > 120 && (
          <p className="px-3 py-2 font-mono text-[11px] text-terminal-muted">
            Showing top 120 by current sort — tighten filters to narrow.
          </p>
        )}
      </div>
    </div>
  );
}
