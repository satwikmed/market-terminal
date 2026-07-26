import { useEffect, useState } from 'react';
import { api, type SystemStatus } from '../lib/api';

const STATUS_STYLE: Record<string, string> = {
  live: 'text-up border-up/50',
  synthetic: 'text-terminal-warn border-terminal-warn/50',
  disabled: 'text-terminal-muted border-terminal-border',
  empty: 'text-terminal-warn border-terminal-warn/50',
  unavailable: 'text-down border-down/50',
};

function freshness(source: SystemStatus['sources'][number]): string {
  if (source.age_minutes != null) {
    if (source.age_minutes < 60) return `${Math.round(source.age_minutes)} min ago`;
    const hours = source.age_minutes / 60;
    if (hours < 48) return `${hours.toFixed(1)} hours ago`;
    return `${Math.round(hours / 24)} days ago`;
  }
  if (source.last_updated) return source.last_updated;
  return 'on demand';
}

export function StatusPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .status()
      .then(setStatus)
      .catch(() => setError('Could not reach the API.'));
  }, []);

  if (error) return <p className="py-20 text-center font-mono text-terminal-warn">{error}</p>;
  if (!status) return <p className="py-20 text-center font-mono text-terminal-muted">Loading…</p>;

  return (
    <div className="space-y-6 fade-up max-w-5xl">
      <div className="border-b border-terminal-border pb-4">
        <h2 className="text-3xl font-semibold tracking-tight">Where this data comes from</h2>
        <p className="text-sm text-terminal-muted mt-2 max-w-2xl leading-relaxed">
          Most finance demos quietly ship fake numbers. This page exists so you don't have to take
          anything here on faith: every source, its current state, and how stale it is.
        </p>
        <div className="mt-3 flex flex-wrap gap-4 font-mono text-[11px] text-terminal-muted">
          <span>
            Mode: <span className="text-terminal-accent">{status.mode}</span>
          </span>
          <span>
            Market: <span className="text-terminal-accent">{status.market.label}</span>
          </span>
          <span>Server time: {status.server_time}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {status.sources.map((s) => (
          <section key={s.id} className="border border-terminal-border bg-terminal-panel/30 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold">{s.label}</h3>
                <p className="font-mono text-[11px] text-terminal-muted mt-0.5">{s.provider}</p>
              </div>
              <span
                className={`font-mono text-[10px] uppercase tracking-wider px-2 py-1 border ${
                  STATUS_STYLE[s.status] ?? 'text-terminal-muted border-terminal-border'
                }`}
              >
                {s.status}
              </span>
            </div>
            <div className="mt-3 flex gap-6 font-mono text-[11px] text-terminal-muted tabular-nums">
              {s.records != null && <span>{s.records.toLocaleString()} records</span>}
              <span>Updated {freshness(s)}</span>
            </div>
            <p className="text-sm text-terminal-muted mt-2 leading-relaxed">{s.notes}</p>
          </section>
        ))}
      </div>

      <section className="border border-terminal-border bg-terminal-panel/30 p-4">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
          Automatic refresh
        </h3>
        {!status.scheduler.running ? (
          <p className="mt-3 text-sm text-terminal-muted">
            The background scheduler is off. Data updates only when refreshed manually.
          </p>
        ) : (
          <>
            <p className="mt-2 text-sm text-terminal-muted">
              Quotes refresh on a loop while markets are open. Fundamentals and price history rebuild
              after the close, and macro series update each morning.
            </p>
            <table className="mt-3 w-full font-mono text-[11px]">
              <thead className="text-terminal-muted uppercase tracking-wider">
                <tr className="text-left">
                  <th className="pb-2">Job</th>
                  <th className="pb-2">Next run</th>
                  <th className="pb-2">Last result</th>
                </tr>
              </thead>
              <tbody>
                {status.scheduler.jobs.map((j) => {
                  const last = status.scheduler.last_run[j.id];
                  return (
                    <tr key={j.id} className="border-t border-terminal-border/60">
                      <td className="py-1.5">{j.id}</td>
                      <td className="py-1.5 text-terminal-muted">{j.next_run ?? '—'}</td>
                      <td className="py-1.5 text-terminal-muted">
                        {last ? `${last.status} · ${last.at}` : 'not run yet'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </>
        )}
      </section>

      <section className="border border-terminal-border bg-terminal-panel/30 p-4">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
          What this app will not do
        </h3>
        <ul className="mt-3 space-y-2 text-sm text-terminal-muted leading-relaxed list-disc pl-5">
          <li>
            Invent a number. If a source omits a field, it shows as unavailable instead of an
            estimate.
          </li>
          <li>
            Let the AI supply its own facts. Filing translations are bounded to the filing text, and
            move explanations are bounded to evidence computed here.
          </li>
          <li>
            Publish rate-decision probabilities. Those require a futures data feed this project does
            not have, so the field stays empty rather than guessing.
          </li>
          <li>Give investment advice, price targets, or buy/sell signals.</li>
        </ul>
      </section>
    </div>
  );
}
