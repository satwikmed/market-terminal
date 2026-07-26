import { useState, type ReactNode } from 'react';
import { HelpCircle } from 'lucide-react';

type Props = {
  label: string;
  value: ReactNode;
  plainEnglish: string;
  className?: string;
};

export function MetricExplain({ label, value, plainEnglish, className = '' }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className={`relative group border-b border-terminal-border/80 py-3 ${className}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-terminal-muted font-mono flex items-center gap-1.5">
            {label}
            <HelpCircle className="w-3 h-3 opacity-60" />
          </div>
          <div className="mt-1 text-xl font-semibold font-mono tabular-nums text-terminal-text">{value}</div>
        </div>
      </div>
      <p className="mt-1.5 text-sm text-terminal-muted leading-snug max-w-prose">{plainEnglish}</p>
      {open && (
        <div className="absolute z-20 left-0 right-0 top-full mt-1 p-3 bg-terminal-text text-terminal-panel border-l-4 border-terminal-accent text-sm shadow-lg fade-up">
          <span className="text-terminal-accent font-mono text-[10px] uppercase tracking-widest">
            Explain like I&apos;m 5
          </span>
          <p className="mt-1 leading-relaxed text-white/85">{plainEnglish}</p>
        </div>
      )}
    </div>
  );
}
