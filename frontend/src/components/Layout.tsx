import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { SignalAtmosphere } from './SignalAtmosphere';
import { TickerTape } from './TickerTape';

const links = [
  { to: '/map', label: 'Map' },
  { to: '/screener', label: 'Screener' },
  { to: '/risk', label: 'Risk' },
  { to: '/portfolio', label: 'Portfolio' },
  { to: '/compare', label: 'Compare' },
  { to: '/macro', label: 'Economy' },
  { to: '/brief', label: 'Brief' },
  { to: '/data', label: 'Sources' },
];

export function Layout() {
  const { pathname } = useLocation();
  const isMap = pathname === '/map';

  return (
    <div
      className={`relative min-h-full terminal-grid flex flex-col ${isMap ? 'h-dvh overflow-hidden' : ''}`}
    >
      {!isMap && (
        <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden" aria-hidden>
          <SignalAtmosphere intensity="whisper" />
        </div>
      )}

      <header className="relative z-40 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-stretch border-b-2 border-terminal-text">
          <NavLink
            to="/"
            className="group flex items-center gap-3 px-4 md:px-6 py-3 bg-terminal-text text-terminal-panel hover:bg-terminal-accent transition-colors shrink-0"
          >
            <span className="brand-mark text-xl md:text-2xl tracking-tight">Lumen</span>
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] opacity-70 group-hover:opacity-100 leading-tight">
              S&amp;P 500
              <br />
              in plain English
            </span>
          </NavLink>

          <div className="flex-1 flex flex-wrap items-center justify-between gap-3 px-4 md:px-6 py-3 bg-terminal-panel/90 backdrop-blur-[2px]">
            <p className="hidden md:block text-sm text-terminal-muted max-w-md leading-snug">
              Map · filings · macro, explained without jargon. Public sources, plainly labeled.
            </p>
            <nav className="flex flex-wrap items-center gap-1 ml-auto font-mono text-[11px] uppercase tracking-[0.14em]">
              {links.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  end={l.to === '/map'}
                  className={({ isActive }) =>
                    `px-2.5 py-1.5 transition-colors ${
                      isActive
                        ? 'text-terminal-accent underline decoration-2 underline-offset-4'
                        : 'text-terminal-muted hover:text-terminal-text'
                    }`
                  }
                >
                  {l.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </div>
        <TickerTape />
      </header>

      <main
        className={`relative z-10 flex-1 w-full ${isMap ? 'min-h-0 relative' : 'max-w-[1600px] mx-auto px-4 md:px-6 py-6'}`}
      >
        <Outlet />
      </main>

      {!isMap && (
        <footer className="relative z-10 border-t-2 border-terminal-text py-3 px-4 md:px-6 font-mono text-[11px] text-terminal-muted flex flex-wrap gap-x-4 gap-y-1 justify-between max-w-[1600px] mx-auto w-full">
          <span>
            Done by{' '}
            <a
              href="https://satwikmedipalli.dev"
              target="_blank"
              rel="noreferrer"
              className="text-terminal-accent hover:underline"
            >
              Satwik Medipalli
            </a>
          </span>
          <span>
            Yahoo · SEC EDGAR · FRED ·{' '}
            <NavLink to="/data" className="text-terminal-accent hover:underline">
              every source listed
            </NavLink>
          </span>
        </footer>
      )}
    </div>
  );
}
