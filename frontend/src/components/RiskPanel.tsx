import { useEffect, useState } from 'react';
import { api, type RiskMetrics } from '../lib/api';

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="border border-terminal-border/70 p-2.5">
      <div className="font-mono text-[9px] uppercase tracking-[0.12em] text-terminal-muted">{label}</div>
      <div className="mt-0.5 text-lg font-semibold font-mono tabular-nums text-terminal-text">{value}</div>
      {hint && <div className="text-[10px] text-terminal-muted leading-tight mt-0.5">{hint}</div>}
    </div>
  );
}

export function RiskPanel({ ticker }: { ticker: string }) {
  const [r, setR] = useState<RiskMetrics | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    let alive = true;
    setR(null);
    setMissing(false);
    api
      .risk(ticker)
      .then((d) => alive && setR(d))
      .catch(() => alive && setMissing(true));
    return () => {
      alive = false;
    };
  }, [ticker]);

  if (missing) {
    return (
      <section className="panel-plain p-4">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Risk profile</h3>
        <p className="mt-3 text-sm text-terminal-muted">Not enough price history to compute risk metrics.</p>
      </section>
    );
  }
  if (!r) {
    return (
      <section className="panel-plain p-4">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Risk profile</h3>
        <p className="mt-3 text-sm text-terminal-muted">Computing from 2 years of daily closes…</p>
      </section>
    );
  }

  const range = r.week52_high - r.week52_low;
  const pos = range > 0 ? ((r.price - r.week52_low) / range) * 100 : 50;

  return (
    <section className="panel-plain p-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">Risk profile · 2-year</h3>
        <span className="font-mono text-[10px] text-terminal-muted">{r.observations} sessions vs {r.benchmark}</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mt-3">
        <Stat label="Beta" value={r.beta?.toFixed(2) ?? '—'} hint={r.beta != null ? (r.beta > 1 ? 'Swings more than market' : 'Steadier than market') : undefined} />
        <Stat label="Volatility" value={`${r.annualized_volatility_pct}%`} hint="Annualized" />
        <Stat label="Sharpe" value={r.sharpe_ratio?.toFixed(2) ?? '—'} hint="Return per unit risk" />
        <Stat label="Max drawdown" value={`${r.max_drawdown_pct}%`} hint="Worst peak-to-trough" />
        <Stat label="2Y return" value={`${r.annualized_return_pct}%`} hint="Annualized" />
        <Stat label="RSI(14)" value={r.rsi_14?.toFixed(0) ?? '—'} hint={r.rsi_14 != null ? (r.rsi_14 > 70 ? 'Overbought' : r.rsi_14 < 30 ? 'Oversold' : 'Neutral') : undefined} />
      </div>

      <div className="mt-4">
        <div className="flex justify-between font-mono text-[10px] text-terminal-muted mb-1">
          <span>52-wk low ${r.week52_low.toFixed(2)}</span>
          <span>${r.price.toFixed(2)}</span>
          <span>${r.week52_high.toFixed(2)} high</span>
        </div>
        <div className="relative h-2 bg-terminal-border/50">
          <div className="absolute top-0 bottom-0 w-1 bg-terminal-accent" style={{ left: `calc(${Math.max(0, Math.min(100, pos))}% - 2px)` }} />
        </div>
      </div>

      {r.sma_50 != null && r.sma_200 != null && (
        <p className="mt-3 font-mono text-[11px] text-terminal-muted">
          50-day ${r.sma_50.toFixed(2)} · 200-day ${r.sma_200.toFixed(2)} ·{' '}
          <span className={r.ma_cross === 'golden' ? 'text-up' : 'text-down'}>
            {r.ma_cross === 'golden' ? 'golden cross (uptrend)' : 'death cross (downtrend)'}
          </span>
        </p>
      )}
      <p className="mt-1 font-mono text-[10px] text-terminal-muted">
        Risk-free {r.risk_free_pct}% · computed here from stored daily bars.
      </p>
    </section>
  );
}
