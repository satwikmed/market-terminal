import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from 'recharts';
import { FilingsPanel } from '../components/FilingsPanel';
import { FinancialsSection } from '../components/FinancialsSection';
import { MetricExplain } from '../components/MetricExplain';
import { MoveAnalysis } from '../components/MoveAnalysis';
import { RiskPanel } from '../components/RiskPanel';
import {
  api,
  formatMoney,
  formatPct,
  type CompanyDetail,
  type Relationship,
} from '../lib/api';

export function CompanyPage() {
  const { ticker = '' } = useParams();
  const [company, setCompany] = useState<CompanyDetail | null>(null);
  const [history, setHistory] = useState<{ date: string; close: number }[]>([]);
  const [rels, setRels] = useState<Relationship[]>([]);
  const [analogy, setAnalogy] = useState<{ headline: string; comparisons: { sentence: string }[]; share_text: string } | null>(null);
  const [earnings, setEarnings] = useState<{
    summary: string;
    citation: { form: string; filing_date: string; source_url: string; section_label: string } | null;
  } | null>(null);
  const [holders, setHolders] = useState<{ name: string; pct: number; plain: string }[]>([]);
  const [insiders, setInsiders] = useState<{ person: string; action: string; plain: string }[]>([]);
  const [ownershipSource, setOwnershipSource] = useState<string | null>(null);
  const [insiderSource, setInsiderSource] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [events, setEvents] = useState<{ date: string; title: string }[]>([]);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let alive = true;
    setCompany(null);
    setHolders([]);
    setInsiders([]);
    setOwnershipSource(null);
    setInsiderSource(null);
    (async () => {
      try {
        const [c, h, r, a, macro] = await Promise.all([
          api.company(ticker),
          api.history(ticker),
          api.relationships(ticker),
          api.analogy(ticker),
          api.macro(),
        ]);
        if (!alive) return;
        setCompany(c);
        setHistory(h.map((p) => ({ date: p.date, close: p.close })));
        setRels(r);
        setAnalogy(a);
        setEvents(macro.events.map((e) => ({ date: e.date, title: e.title })));
        setEarnings(null);

        const [institutionsResult, insidersResult] = await Promise.allSettled([
          api.institutions(ticker),
          api.insiders(ticker),
        ]);
        if (!alive) return;
        if (institutionsResult.status === 'fulfilled') {
          setHolders(institutionsResult.value.holders);
          setOwnershipSource(
            `${institutionsResult.value.source} · as of ${institutionsResult.value.as_of ?? 'latest filing'}`,
          );
        } else {
          setHolders([]);
          setOwnershipSource('Live ownership data temporarily unavailable');
        }
        if (insidersResult.status === 'fulfilled') {
          setInsiders(insidersResult.value.activity);
          setInsiderSource(
            `${insidersResult.value.source} · as of ${insidersResult.value.as_of ?? 'latest filing'}`,
          );
        } else {
          setInsiders([]);
          setInsiderSource('Live insider data temporarily unavailable');
        }
      } catch (err) {
        console.error(err);
        if (alive) setCompany(null);
      }
    })();
    return () => {
      alive = false;
    };
  }, [ticker]);

  if (!company) {
    return (
      <div className="py-20 text-center font-mono text-terminal-muted">
        Loading {ticker.toUpperCase()}… or ticker not in S&P 500 universe.
        <div className="mt-4">
          <Link to="/map" className="text-terminal-accent">
            ← Back to map
          </Link>
        </div>
      </div>
    );
  }

  const up = (company.change_pct ?? 0) >= 0;

  return (
    <div className="space-y-8 fade-up">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b-2 border-terminal-text pb-5">
        <div>
          <Link
            to="/map"
            className="font-mono text-[11px] text-terminal-muted hover:text-terminal-accent uppercase tracking-[0.14em]"
          >
            ← Map
          </Link>
          <h2 className="brand-mark text-[clamp(2rem,5vw,3.5rem)] mt-3">
            <span className="text-terminal-accent">{company.ticker}</span>{' '}
            <span className="text-terminal-text">{company.name}</span>
          </h2>
          <p className="text-sm text-terminal-muted mt-2 font-mono uppercase tracking-wider">
            {company.sector} · {company.industry}
          </p>
        </div>
        <div className="text-right">
          <div className="font-mono text-4xl tabular-nums tracking-tight">
            ${company.price?.toFixed(2) ?? '—'}
          </div>
          <div className={`font-mono text-sm mt-1 ${up ? 'text-up' : 'text-down'}`}>
            {formatPct(company.change_pct)} · {company.quote_label}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 panel-plain p-4">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-muted mb-3">
            Price · with macro event markers
          </h3>
          <div className="h-72">
            {history.length === 0 ? (
              <div className="h-full grid place-items-center text-sm text-terminal-muted">
                Chart history seeds for spotlight names first — try AAPL, NVDA, MSFT.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history}>
                  <CartesianGrid stroke="rgba(10,11,14,0.08)" />
                  <XAxis dataKey="date" tick={{ fill: '#5a6270', fontSize: 10 }} minTickGap={40} />
                  <YAxis domain={['auto', 'auto']} tick={{ fill: '#5a6270', fontSize: 10 }} width={48} />
                  <Tooltip
                    contentStyle={{
                      background: '#0a0b0e',
                      border: '1px solid #0a0b0e',
                      color: '#f3f4f8',
                      fontFamily: 'JetBrains Mono',
                    }}
                  />
                  <Line type="monotone" dataKey="close" stroke="#ff2400" dot={false} strokeWidth={1.8} />
                  {events
                    .filter((e) => history.some((h) => h.date >= e.date))
                    .slice(0, 4)
                    .map((e) => (
                      <ReferenceLine
                        key={e.date + e.title}
                        x={e.date}
                        stroke="#b45309"
                        strokeDasharray="3 3"
                        label={{ value: e.title.split(' ')[0], fill: '#b45309', fontSize: 9 }}
                      />
                    ))}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
          <p className="text-xs text-terminal-muted mt-2">
            Dashed lines mark major economic releases so you can visually connect macro news to price action.
          </p>
        </div>

        <div className="panel-plain p-4">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
            Explain like I&apos;m 5
          </h3>
          {company.metrics.map((m) => (
            <MetricExplain key={m.metric} label={m.metric} value={m.value_display} plainEnglish={m.plain_english} />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="panel-plain p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Analogy engine</h3>
            <button
              type="button"
              className="font-mono text-[11px] uppercase tracking-wider px-2 py-1 border border-terminal-border hover:border-terminal-accent text-terminal-muted hover:text-terminal-accent"
              onClick={async () => {
                if (!analogy) return;
                await navigator.clipboard.writeText(analogy.share_text);
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              }}
            >
              {copied ? 'Copied' : 'Copy / Share'}
            </button>
          </div>
          <p className="text-xl font-semibold mt-3">{analogy?.headline}</p>
          <ul className="mt-3 space-y-2">
            {analogy?.comparisons.map((c) => (
              <li key={c.sentence} className="text-sm text-terminal-muted leading-relaxed">
                {c.sentence}
              </li>
            ))}
          </ul>
        </section>

        <section className="panel-plain p-4">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Business relationships</h3>
          <ul className="mt-3 space-y-3 max-h-64 overflow-auto">
            {rels.length === 0 && <li className="text-sm text-terminal-muted">Curated coverage expanding — major names first.</li>}
            {rels.map((r) => (
              <li key={r.target_ticker}>
                <Link to={`/company/${r.target_ticker}`} className="font-mono text-terminal-accent hover:underline">
                  {r.target_ticker}
                </Link>
                <span className="ml-2 text-[10px] uppercase text-terminal-warn font-mono">{r.relationship_type}</span>
                <p className="text-sm text-terminal-muted mt-0.5">{r.plain_english}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <RiskPanel ticker={company.ticker} />

      <FinancialsSection ticker={company.ticker} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MoveAnalysis ticker={company.ticker} />
        <FilingsPanel ticker={company.ticker} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <section className="panel-plain p-4">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
            Earnings, explained
          </h3>
          <p className="text-xs text-terminal-muted mt-2">
            Summarised from the company's own Management's Discussion section in its latest quarterly
            or annual report.
          </p>
          <button
            type="button"
            disabled={busy === 'earnings'}
            onClick={async () => {
              setBusy('earnings');
              try {
                const r = await api.earnings(company.ticker);
                setEarnings({ summary: r.summary, citation: r.citation });
              } finally {
                setBusy(null);
              }
            }}
            className="mt-3 w-full text-left px-3 py-2 border border-terminal-border hover:border-terminal-accent font-mono text-xs uppercase tracking-wider disabled:opacity-50"
          >
            {busy === 'earnings' ? 'Reading the filing…' : 'Summarize the latest results'}
          </button>
          {earnings && (
            <div className="mt-3">
              <p className="text-sm text-terminal-muted leading-relaxed whitespace-pre-wrap">
                {earnings.summary}
              </p>
              {earnings.citation && (
                <a
                  href={earnings.citation.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-block font-mono text-[10px] text-terminal-accent hover:underline"
                >
                  Source: {earnings.citation.form} filed {earnings.citation.filing_date} ↗
                </a>
              )}
            </div>
          )}
        </section>

        <section className="panel-plain p-4">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Institutional ownership</h3>
          {ownershipSource && (
            <p className="mt-2 text-[10px] font-mono text-terminal-muted">{ownershipSource}</p>
          )}
          <ul className="mt-3 space-y-3">
            {holders.length === 0 && (
              <li className="text-sm text-terminal-muted">No live holdings available right now.</li>
            )}
            {holders.map((h) => (
              <li key={h.name}>
                <div className="flex justify-between font-mono text-sm">
                  <span>{h.name}</span>
                  <span>{h.pct.toFixed(1)}%</span>
                </div>
                <p className="text-sm text-terminal-muted">{h.plain}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel-plain p-4">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Insider activity</h3>
          {insiderSource && (
            <p className="mt-2 text-[10px] font-mono text-terminal-muted">{insiderSource}</p>
          )}
          <ul className="mt-3 space-y-3">
            {insiders.length === 0 && (
              <li className="text-sm text-terminal-muted">No recent live transactions available.</li>
            )}
            {insiders.map((row, i) => (
              <li key={i}>
                <div className="font-mono text-sm">
                  {row.person} · <span className={row.action === 'buy' ? 'text-up' : 'text-down'}>{row.action}</span>
                </div>
                <p className="text-sm text-terminal-muted mt-1">{row.plain}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <p className="text-xs text-terminal-muted font-mono">
        Market cap {formatMoney(company.market_cap)} · Educational demo · Not investment advice
      </p>
    </div>
  );
}
