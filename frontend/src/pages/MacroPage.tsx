import { useEffect, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { MetricExplain } from '../components/MetricExplain';
import { api, type MacroDashboard } from '../lib/api';

export function MacroPage() {
  const [data, setData] = useState<MacroDashboard | null>(null);

  useEffect(() => {
    api.macro().then(setData).catch(() => setData(null));
  }, []);

  if (!data) {
    return <div className="py-20 text-center font-mono text-terminal-muted">Loading US economy layer…</div>;
  }

  const yieldSeries = data.indicators.find((i) => i.id === 'T10Y2Y');
  const recession = data.indicators.find((i) => i.id === 'RECESSION_PROB');

  return (
    <div className="space-y-6 fade-up">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">US Economy</h2>
        <p className="text-sm text-terminal-muted mt-1 max-w-2xl">
          Macro numbers from FRED-style series, translated into plain English, then connected back to how sectors on the bubble map tend to react.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {data.indicators
          .filter((i) => i.id !== 'T10Y2Y' && i.id !== 'RECESSION_PROB')
          .map((ind) => (
            <div key={ind.id} className="border border-terminal-border bg-terminal-panel/30 px-4">
              <MetricExplain
                label={ind.label}
                value={`${ind.value.toFixed(2)}${ind.unit === '%' ? '%' : ''}`}
                plainEnglish={ind.plain_english}
              />
              <div className="h-20 pb-3">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={ind.history}>
                    <Line type="monotone" dataKey="value" stroke="#3dd6c6" dot={false} strokeWidth={1.4} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="border border-terminal-border bg-terminal-panel/30 p-4">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Fed rate tracker</h3>
          <p className="text-3xl font-mono mt-3 tabular-nums">
            Next FOMC · {data.fed.next_fomc}
            {data.fed.days_until != null && (
              <span className="text-base text-terminal-muted ml-3">{data.fed.days_until}d</span>
            )}
          </p>
          <div className="mt-4 grid grid-cols-3 gap-2 font-mono text-center">
            {(['cut', 'hold', 'hike'] as const).map((k) => (
              <div key={k} className="border border-terminal-border py-3">
                <div className="text-[10px] uppercase text-terminal-muted tracking-wider">{k}</div>
                <div className="text-xl mt-1">
                  {data.fed.probabilities[k] == null ? '—' : `${data.fed.probabilities[k]}%`}
                </div>
              </div>
            ))}
          </div>
          <p className="text-sm text-terminal-muted mt-4 leading-relaxed">{data.fed.plain_english}</p>
          <p className="text-xs text-terminal-muted mt-2 font-mono">
            {data.fed.probabilities_available
              ? 'Market-implied odds are estimates, not promises.'
              : 'Probability data withheld until a reliable licensed source is connected.'}
          </p>
        </section>

        <section className="border border-terminal-border bg-terminal-panel/30 p-4">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Inflation basket</h3>
          <p className="text-sm text-terminal-muted mt-1">What's actually pushing the CPI number around.</p>
          <div className="h-56 mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.inflation_basket}>
                <CartesianGrid stroke="rgba(28,37,51,0.9)" vertical={false} />
                <XAxis dataKey="component" tick={{ fill: '#7a8799', fontSize: 10 }} />
                <YAxis tick={{ fill: '#7a8799', fontSize: 10 }} unit="%" />
                <Tooltip contentStyle={{ background: '#0f141c', border: '1px solid #1c2533' }} />
                <Bar dataKey="value" fill="#f0b429" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="border border-terminal-border bg-terminal-panel/30 p-4">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Yield curve · 2s10s</h3>
          <div className="h-56 mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={yieldSeries?.history ?? []}>
                <CartesianGrid stroke="rgba(28,37,51,0.9)" />
                <XAxis dataKey="date" tick={{ fill: '#7a8799', fontSize: 10 }} minTickGap={30} />
                <YAxis tick={{ fill: '#7a8799', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#0f141c', border: '1px solid #1c2533' }} />
                <Line type="monotone" dataKey="value" stroke="#7aa2f7" dot={false} strokeWidth={1.6} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="text-sm text-terminal-muted mt-3 leading-relaxed">{data.yield_curve_note}</p>
        </section>

        <section className="border border-terminal-border bg-terminal-panel/30 p-4">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Recession probability</h3>
          <p className="text-4xl font-mono mt-3 tabular-nums text-terminal-warn">
            {recession?.value.toFixed(0) ?? '—'}%
          </p>
          <p className="text-sm text-terminal-muted mt-2 leading-relaxed">{recession?.plain_english}</p>
          <h4 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-muted mt-6">Economic calendar</h4>
          <ul className="mt-2 space-y-2 max-h-40 overflow-auto">
            {data.events.map((e) => (
              <li key={e.date + e.title} className="text-sm border-b border-terminal-border/60 pb-2">
                <span className="font-mono text-terminal-accent">{e.date}</span> · {e.title}
                <p className="text-terminal-muted text-xs mt-0.5">{e.plain_english}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="border border-terminal-border bg-terminal-panel/30 p-4">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
          Sector rate sensitivity · connective tissue
        </h3>
        <p className="text-sm text-terminal-muted mt-1 mb-4">
          Toggle “Rate Sensitivity” on the bubble map to color sectors by this historical pattern.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
          {Object.entries(data.rate_sensitivity)
            .sort((a, b) => a[1] - b[1])
            .map(([sector, score]) => (
              <div key={sector} className="border border-terminal-border px-3 py-2 font-mono text-sm flex justify-between">
                <span className="text-terminal-muted truncate pr-2">{sector}</span>
                <span className={score < 0 ? 'text-down' : 'text-up'}>{score.toFixed(2)}</span>
              </div>
            ))}
        </div>
      </section>

      {data.data_sources && (
        <section className="border border-terminal-border bg-terminal-panel/30 p-4 text-xs text-terminal-muted">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
            Data provenance
          </h3>
          <p className="mt-2">{data.data_sources.macro}</p>
          <p className="mt-1">{data.data_sources.fomc}</p>
          <p className="mt-1">{data.data_sources.rate_sensitivity}</p>
        </section>
      )}
    </div>
  );
}
