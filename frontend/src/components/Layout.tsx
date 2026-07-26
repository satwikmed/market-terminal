import { NavLink, Outlet } from 'react-router-dom';
import { TickerTape } from './TickerTape';

const links = [
  { to: '/', label: 'Bubble Map' },
  { to: '/macro', label: 'US Economy' },
  { to: '/brief', label: 'Weekly Brief' },
  { to: '/data', label: 'Data & Sources' },
];

export function Layout() {
  return (
    <div className="min-h-full terminal-grid flex flex-col">
      <header className="border-b border-terminal-border bg-terminal-bg/80 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-[1600px] mx-auto px-4 py-3 flex items-end justify-between gap-6">
          <div className="fade-up">
            <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-terminal-accent">S&P 500 · Plain English</div>
            <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-terminal-text mt-0.5">
              Plain English Terminal
            </h1>
            <p className="text-sm text-terminal-muted mt-1 max-w-xl">
              Bloomberg density, beginner clarity — every number explained.
            </p>
          </div>
          <nav className="flex items-center gap-1 font-mono text-xs uppercase tracking-wider">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.to === '/'}
                className={({ isActive }) =>
                  `px-3 py-2 border transition-colors ${
                    isActive
                      ? 'border-terminal-accent text-terminal-accent bg-terminal-accent/10'
                      : 'border-transparent text-terminal-muted hover:text-terminal-text hover:border-terminal-border'
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <TickerTape />
      </header>
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-4 py-4">
        <Outlet />
      </main>
      <footer className="border-t border-terminal-border py-3 px-4 text-[11px] font-mono text-terminal-muted flex flex-wrap gap-x-4 gap-y-1 justify-between max-w-[1600px] mx-auto w-full">
        <span>Equities · S&P 500 only · Not investment advice</span>
        <span>
          Yahoo prices · SEC EDGAR filings · FRED macro ·{' '}
          <NavLink to="/data" className="text-terminal-accent hover:underline">
            every source listed here
          </NavLink>
        </span>
      </footer>
    </div>
  );
}
