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
    <div className="bg-terminal-text text-terminal-panel">
      <div className="flex items-center gap-3 px-4 md:px-6 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-white/55 border-b border-white/15">
        <span className="flex items-center gap-1.5 text-white/80">
          <span className={`w-1.5 h-1.5 rounded-full ${isLive ? 'bg-up live-dot' : 'bg-terminal-accent'}`} />
          {isLive ? 'Market open' : 'Market closed'}
        </span>
        <span className="text-terminal-accent">{label}</span>
        <span className="hidden sm:inline">S&amp;P 500</span>
      </div>
      <div className="overflow-hidden whitespace-nowrap py-2.5 tape-mask">
        <div className="tape-track inline-flex min-w-full">
          {loop.map((q, i) => {
            const up = q.change_pct >= 0;
            return (
              <Link
                key={`${q.ticker}-${i}`}
                to={`/company/${q.ticker}`}
                className="inline-flex items-baseline gap-2 px-4 font-mono text-sm hover:bg-white/10 transition-colors"
              >
                <span className="font-semibold text-white">{q.ticker}</span>
                <span className="text-white/45">${q.price.toFixed(2)}</span>
                <span className={up ? 'text-[#3ecf8e]' : 'text-[#ff8a8a]'}>{formatPct(q.change_pct)}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
