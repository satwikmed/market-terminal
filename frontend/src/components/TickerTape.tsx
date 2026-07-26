import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, formatPct, type Quote } from '../lib/api';

export function TickerTape() {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [label, setLabel] = useState('Loading');
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const data = await api.tape();
        if (!alive) return;
        setQuotes(data.quotes);
        setLabel(data.session_label);
        setIsLive(data.is_live);
      } catch {
        /* keep last */
      }
    };
    load();
    const id = setInterval(load, 45_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const loop = [...quotes, ...quotes];

  return (
    <div className="border-b border-terminal-border bg-terminal-panel/90 backdrop-blur-sm">
      <div className="flex items-center gap-3 px-3 py-1.5 text-[11px] font-mono uppercase tracking-wider text-terminal-muted border-b border-terminal-border/60">
        <span className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${isLive ? 'bg-up live-dot' : 'bg-terminal-warn'}`} />
          {isLive ? 'Market Open' : 'Market Closed'}
        </span>
        <span className="text-terminal-accent">{label}</span>
        <span className="hidden sm:inline">S&P 500 · poll 45s</span>
      </div>
      <div className="overflow-hidden whitespace-nowrap py-2">
        <div className="tape-track inline-flex min-w-full">
          {loop.map((q, i) => {
            const up = q.change_pct >= 0;
            return (
              <Link
                key={`${q.ticker}-${i}`}
                to={`/company/${q.ticker}`}
                className="inline-flex items-baseline gap-2 px-4 font-mono text-sm hover:bg-white/5 transition-colors"
              >
                <span className="text-terminal-text font-semibold">{q.ticker}</span>
                <span className="text-terminal-muted">${q.price.toFixed(2)}</span>
                <span className={up ? 'text-up' : 'text-down'}>
                  {up ? '+' : ''}
                  {q.change.toFixed(2)} ({formatPct(q.change_pct)})
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
