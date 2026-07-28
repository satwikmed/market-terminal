import { useEffect, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  ComposedChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api, formatMoney, type Financials } from '../lib/api';

const RATIO_LABELS: { key: string; label: string; suffix: string; plain: string }[] = [
  { key: 'gross_margin', label: 'Gross margin', suffix: '%', plain: 'Cents of gross profit per $1 of sales.' },
  { key: 'operating_margin', label: 'Operating margin', suffix: '%', plain: 'Profit from core operations per $1 of sales.' },
  { key: 'net_margin', label: 'Net margin', suffix: '%', plain: 'Bottom line profit per $1 of sales.' },
  { key: 'roe', label: 'Return on equity', suffix: '%', plain: 'Profit generated on shareholder capital.' },
  { key: 'roa', label: 'Return on assets', suffix: '%', plain: 'Profit generated on total assets.' },
  { key: 'fcf_margin', label: 'FCF margin', suffix: '%', plain: 'Free cash flow per $1 of sales.' },
  { key: 'debt_to_equity', label: 'Debt / equity', suffix: '×', plain: 'Long term debt relative to equity.' },
  { key: 'current_ratio', label: 'Current ratio', suffix: '×', plain: 'Short term assets vs short term bills.' },
  { key: 'revenue_cagr', label: 'Revenue CAGR', suffix: '%', plain: 'Annualized sales growth over the window.' },
  { key: 'rnd_intensity', label: 'R&D intensity', suffix: '%', plain: 'R&D spend per $1 of sales.' },
];

export function FinancialsSection({ ticker }: { ticker: string }) {
  const [data, setData] = useState<Financials | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    let alive = true;
    setData(null);
    setMissing(false);
    api
      .fundamentals(ticker)
      .then((d) => alive && setData(d))
      .catch(() => alive && setMissing(true));
    return () => {
      alive = false;
    };
  }, [ticker]);

  if (missing) {
    return (
      <section className="panel-plain p-4">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Financial statements</h3>
        <p className="mt-3 text-sm text-terminal-muted">SEC XBRL facts aren&apos;t available for this company right now.</p>
      </section>
    );
  }
  if (!data) {
    return (
      <section className="panel-plain p-4">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Financial statements</h3>
        <p className="mt-3 text-sm text-terminal-muted">Pulling filings from SEC EDGAR…</p>
      </section>
    );
  }

  const years = data.fiscal_years;
  const inc = data.statements.income;
  const cf = data.statements.cashflow;
  const chartData = years.map((y, i) => ({
    year: `FY${String(y).slice(2)}`,
    revenue: inc.revenue[i],
    net_income: inc.net_income[i],
    fcf: cf.free_cash_flow[i],
  }));

  return (
    <section className="panel-plain p-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
          Financial statements · from SEC filings
        </h3>
        <a href={data.source_url} target="_blank" rel="noreferrer" className="font-mono text-[10px] text-terminal-muted hover:text-terminal-accent">
          {data.fiscal_years[0]} to {data.latest_fiscal_year} · EDGAR ↗
        </a>
      </div>

      {data.negative_equity && (
        <p className="mt-3 border-l-2 border-terminal-warn/60 pl-2.5 text-xs text-terminal-muted leading-relaxed">
          Book equity is negative: years of buybacks have exceeded retained earnings. Return on
          equity and debt/equity divide by that figure, so they are not meaningful and are left
          blank rather than shown as large negative numbers.
        </p>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 mt-3">
        {RATIO_LABELS.map((r) => {
          const v = data.ratios[r.key];
          return (
            <div key={r.key} className="border border-terminal-border/70 p-2.5 group relative">
              <div className="font-mono text-[9px] uppercase tracking-[0.1em] text-terminal-muted">{r.label}</div>
              <div className="mt-0.5 text-lg font-semibold font-mono tabular-nums text-terminal-text">
                {v == null ? 'n/a' : `${v}${r.suffix}`}
              </div>
              <div className="text-[10px] text-terminal-muted leading-tight mt-0.5">{r.plain}</div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-5">
        <div>
          <h4 className="font-mono text-[10px] uppercase tracking-wider text-terminal-muted mb-2">
            Revenue &amp; net income
          </h4>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData}>
                <CartesianGrid stroke="rgba(10,11,14,0.08)" vertical={false} />
                <XAxis dataKey="year" tick={{ fill: '#5a6270', fontSize: 10 }} />
                <YAxis tick={{ fill: '#5a6270', fontSize: 10 }} width={44} tickFormatter={(v) => formatMoney(v).replace('$', '')} />
                <Tooltip
                  contentStyle={{ background: '#0a0b0e', border: 'none', color: '#f3f4f8', fontFamily: 'JetBrains Mono', fontSize: 12 }}
                  formatter={(value, name) => [formatMoney(Number(value)), name === 'revenue' ? 'Revenue' : 'Net income']}
                />
                <Bar dataKey="revenue" fill="#c5c9d2" />
                <Line type="monotone" dataKey="net_income" stroke="#ff2400" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div>
          <h4 className="font-mono text-[10px] uppercase tracking-wider text-terminal-muted mb-2">
            Free cash flow
          </h4>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid stroke="rgba(10,11,14,0.08)" vertical={false} />
                <XAxis dataKey="year" tick={{ fill: '#5a6270', fontSize: 10 }} />
                <YAxis tick={{ fill: '#5a6270', fontSize: 10 }} width={44} tickFormatter={(v) => formatMoney(v).replace('$', '')} />
                <Tooltip
                  contentStyle={{ background: '#0a0b0e', border: 'none', color: '#f3f4f8', fontFamily: 'JetBrains Mono', fontSize: 12 }}
                  formatter={(value) => [formatMoney(Number(value)), 'Free cash flow']}
                />
                <Bar dataKey="fcf" fill="#007a4d" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="mt-5 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-terminal-text font-mono text-[10px] uppercase tracking-wider text-terminal-muted">
              <th className="px-2 py-2 text-left">$ millions</th>
              {years.map((y) => (
                <th key={y} className="px-2 py-2 text-right">FY{String(y).slice(2)}</th>
              ))}
            </tr>
          </thead>
          <tbody className="font-mono tabular-nums">
            {[
              { label: 'Revenue', vals: inc.revenue },
              { label: 'Gross profit', vals: inc.gross_profit },
              { label: 'Operating income', vals: inc.operating_income },
              { label: 'Net income', vals: inc.net_income },
              { label: 'Diluted EPS', vals: inc.eps_diluted, isEps: true },
              { label: 'Free cash flow', vals: cf.free_cash_flow },
            ].map((r) => (
              <tr key={r.label} className="border-b border-terminal-border/60">
                <td className="px-2 py-1.5 text-terminal-muted whitespace-nowrap">{r.label}</td>
                {r.vals.map((v, i) => (
                  <td key={i} className="px-2 py-1.5 text-right">
                    {v == null ? 'n/a' : r.isEps ? `$${v.toFixed(2)}` : (v / 1e6).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 font-mono text-[10px] text-terminal-muted">{data.source} · as filed values, not restated.</p>
    </section>
  );
}
