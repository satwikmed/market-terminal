import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { SignalAtmosphere } from '../components/SignalAtmosphere';

const layers = [
  {
    n: '01',
    title: 'Micro: every company, explained',
    body: (
      <>
        All <strong className="text-terminal-text font-semibold">503 current S&amp;P 500 constituents</strong>{' '}
        live in one universe. Open any ticker and you get Yahoo Finance last sale quotes (refreshed
        throughout the session, not SIP / Level&nbsp;1), two years of price history with macro event
        markers, and <strong className="text-terminal-text font-semibold">full financial statements
        pulled straight from SEC XBRL filings</strong>: revenue, margins, cash flow, and a dozen
        computed ratios going back to 2019. Market cap analogies and metric tooltips translate every
        number, so you never have to already know what P/E, beta, or free cash flow mean.
      </>
    ),
  },
  {
    n: '02',
    title: 'Meso: how companies connect',
    body: (
      <>
        The bubble map is the product’s center of gravity: size is market cap, color is today’s move,
        clusters are sectors. Switch into relationship mode and every name has a network: curated
        supplier / customer / partner edges plus explicitly labeled industry peers, so the map is
        explorable end to end, not a handful of famous stocks. A third mode paints sectors by
        historical rate sensitivity, tying the meso view to the macro layer.
      </>
    ),
  },
  {
    n: '03',
    title: 'Macro: the economy behind the tape',
    body: (
      <>
        Inflation, jobs, rates, GDP, the yield curve, and the Fed calendar come from{' '}
        <strong className="text-terminal-text font-semibold">live FRED series</strong> and the official
        FOMC schedule. Observation dates are shown on purpose. Rate decision probabilities stay blank:
        we refuse to invent a futures market we don’t have. Sector rate sensitivity scores feed back
        into the map so macro isn’t a separate brochure: it’s connective tissue.
      </>
    ),
  },
  {
    n: '04',
    title: 'Grounded AI: no invented causes',
    body: (
      <>
        Filing translations pull real Risk Factors / MD&amp;A text from{' '}
        <strong className="text-terminal-text font-semibold">SEC EDGAR</strong> and show the source
        beside the output. “Why did this move?” first decomposes the day into market, industry, and
        company specific pieces, checks volatility and nearby filings, then lets a model narrate{' '}
        <em>only</em> that evidence. With no API key, the deterministic summary still works: the app
        never pretends an LLM is required to be useful.
      </>
    ),
  },
  {
    n: '05',
    title: 'Quant: the analyst toolkit',
    body: (
      <>
        Four working tools, not screenshots. A{' '}
        <strong className="text-terminal-text font-semibold">screener</strong> ranks all 503 names on
        fundamentals and momentum. A <strong className="text-terminal-text font-semibold">risk lab</strong>{' '}
        computes beta, volatility, Sharpe, drawdown, and a correlation heatmap from two years of daily
        returns against SPY. A <strong className="text-terminal-text font-semibold">portfolio
        backtester</strong> replays any weighted basket versus the S&amp;P and attributes every point of
        return. And a <strong className="text-terminal-text font-semibold">compare</strong> view puts four
        companies head to head across valuation, profitability, and risk. Every figure is computed here,
        from stored data: nothing is mocked.
      </>
    ),
  },
  {
    n: '06',
    title: 'Provenance as a feature',
    body: (
      <>
        Ownership and insider activity come from filing derived Yahoo data with report dates.
        Unavailable fundamentals show as unavailable, never as synthetic filler. A few names without
        usable SEC revenue tags fall back to Yahoo TTM for the company row figure only; multi year
        statements stay filing sourced or blank. The Sources page lists every provider, record count,
        and how stale it is, and states plainly what this is not: no Level&nbsp;1 tape, no invented
        odds, no advice.
      </>
    ),
  },
];

/**
 * About / manifesto — Clearing aesthetic, editorial depth.
 */
export function LandingPage() {
  return (
    <div className="min-h-dvh terminal-grid flex flex-col">
      <header className="border-b-2 border-terminal-text flex flex-col sm:flex-row sticky top-0 z-30">
        <div className="bg-terminal-text text-terminal-panel px-5 py-4 flex items-center gap-3">
          <span className="brand-mark text-3xl tracking-tight">Lumen</span>
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] opacity-70 leading-tight">
            S&amp;P 500
            <br />
            in plain English
          </span>
        </div>
        <div className="flex-1 flex items-center justify-between gap-4 px-5 py-3 bg-terminal-panel/95 backdrop-blur-sm">
          <p className="hidden md:block text-sm text-terminal-muted max-w-md">
            Built so a beginner can read the market without being lied to by the UI.
          </p>
          <Link to="/map" className="btn-signal inline-flex items-center gap-2 ml-auto">
            Open the map
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      <main className="flex-1 w-full">
        {/* Hero band */}
        <section className="relative border-b-2 border-terminal-text overflow-hidden min-h-[72vh] flex items-center">
          <SignalAtmosphere intensity="hero" />
          <div
            className="absolute inset-y-0 right-0 w-1/2 max-w-xl opacity-[0.06] pointer-events-none hidden lg:block z-[1]"
            aria-hidden
            style={{
              backgroundImage:
                'repeating-linear-gradient(90deg, #0a0b0e 0 1px, transparent 1px 28px), repeating-linear-gradient(0deg, #0a0b0e 0 1px, transparent 1px 28px)',
            }}
          />
          <div className="relative z-10 max-w-5xl mx-auto px-5 md:px-8 py-14 md:py-20 stamp-in w-full">
            <p className="chapter-num">What we built</p>
            <h1 className="brand-mark mt-3 text-[clamp(2.75rem,8vw,5.75rem)] text-terminal-text max-w-4xl">
              A market terminal
              <br />
              that teaches as it shows
              <span className="text-terminal-accent">.</span>
            </h1>
            <div className="signal-rule mt-5" />
            <p className="mt-6 text-lg md:text-xl text-terminal-muted leading-relaxed max-w-2xl">
              Lumen is a full stack S&amp;P 500 research app for people who are curious about markets
              but allergic to jargon. React + TypeScript on the front, FastAPI + a live data pipeline
              on the back. The point isn’t denser charts: it’s making every number, filing, and price
              move readable without faking data to look smarter.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link to="/map" className="btn-signal inline-flex items-center gap-2">
                Enter the map
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link to="/risk" className="btn-ghost inline-flex items-center gap-2">
                Open the risk lab
              </Link>
            </div>
            <blockquote className="mt-10 max-w-xl border-l-4 border-terminal-accent pl-5 py-1">
              <p className="text-base md:text-lg text-terminal-text leading-snug font-medium tracking-tight">
                “Show me what’s real, tell me what it means, and never invent a cause you can’t
                point to.”
              </p>
              <cite className="mt-2 block font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-muted not-italic">
                Design rule for the whole product
              </cite>
            </blockquote>
          </div>
        </section>

        {/* Why it exists */}
        <section className="max-w-5xl mx-auto px-5 md:px-8 py-12 md:py-14 fade-up">
          <p className="chapter-num">The problem</p>
          <div className="mt-4 grid md:grid-cols-2 gap-8 md:gap-12">
            <div>
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight leading-tight">
                Finance UIs assume you already speak finance.
              </h2>
              <p className="mt-4 text-terminal-muted leading-relaxed">
                Bloomberg style terminals bury beginners in tickers and acronyms. Consumer apps often
                go the other way: friendly UI, fuzzy or synthetic numbers. Lumen sits in the gap:
                real data from Yahoo Finance, SEC EDGAR, and FRED, with plain English explanations
                bolted on as a first class layer, not a tooltip afterthought.
              </p>
            </div>
            <div className="font-mono text-[13px] leading-relaxed text-terminal-muted space-y-3 md:pt-2">
              <p className="text-terminal-text font-semibold uppercase tracking-[0.12em] text-[11px]">
                What “in depth” means here
              </p>
              <p>
                → 500+ companies with Yahoo last sale quotes, fundamentals, and history
              </p>
              <p>
                → A D3 force map you can actually explore (industry · relationships · rates)
              </p>
              <p>
                → Multi year financial statements + 12 ratios from SEC XBRL (not invented)
              </p>
              <p>
                → A quant desk: screener, risk lab, correlation heatmap, portfolio backtester
              </p>
              <p>
                → SEC filings fetched under EDGAR fair access rules, summarized with citations
              </p>
              <p>
                → Move attribution that works before any AI key is configured
              </p>
              <p>
                → A Sources page that admits when something is stale or missing
              </p>
            </div>
          </div>
        </section>

        {/* Six layers */}
        <section className="border-y-2 border-terminal-text bg-terminal-panel/40">
          <div className="max-w-5xl mx-auto px-5 md:px-8 py-4">
            <p className="chapter-num">Six layers</p>
          </div>
          <div className="max-w-5xl mx-auto px-5 md:px-8">
            {layers.map((layer, i) => (
              <article
                key={layer.n}
                className="fade-up grid md:grid-cols-[5.5rem_1fr] gap-3 md:gap-8 border-t border-terminal-border py-8 first:border-t-0"
                style={{ animationDelay: `${60 + i * 50}ms` }}
              >
                <div className="chapter-num pt-1">{layer.n}</div>
                <div>
                  <h2 className="text-xl md:text-2xl font-bold tracking-tight">{layer.title}</h2>
                  <p className="mt-3 text-[15px] md:text-base text-terminal-muted leading-relaxed max-w-2xl">
                    {layer.body}
                  </p>
                </div>
              </article>
            ))}
          </div>
        </section>

        {/* How a session flows */}
        <section className="max-w-5xl mx-auto px-5 md:px-8 py-12 md:py-14 fade-up" style={{ animationDelay: '200ms' }}>
          <p className="chapter-num">A typical session</p>
          <h2 className="mt-3 text-2xl md:text-3xl font-bold tracking-tight max-w-xl">
            From the whole market down to one filing.
          </h2>
          <ol className="mt-8 space-y-0 border-l-2 border-terminal-text ml-2">
            {[
              {
                t: 'Open the map',
                d: 'See all 503 names at once. Spot what’s green or red today. Filter by industry, relationships, or rate sensitivity.',
              },
              {
                t: 'Click a company',
                d: 'Price chart with Fed/economic markers, ELI5 metrics, ownership, insiders, and relationship graph.',
              },
              {
                t: 'Ask why it moved',
                d: 'Get a market / industry / company split plus evidence. Optionally rewrite the narrative with grounded AI.',
              },
              {
                t: 'Read the filing',
                d: 'Pull Risk Factors or MD&A from EDGAR, get a plain English translation, keep the source link.',
              },
              {
                t: 'Zoom out to the economy',
                d: 'Check FRED indicators, the FOMC calendar, and how sectors historically behave when rates move.',
              },
            ].map((step, i) => (
              <li key={step.t} className="relative pl-8 pb-8 last:pb-0">
                <span className="absolute -left-[9px] top-1.5 h-4 w-4 rounded-full bg-terminal-accent border-2 border-terminal-bg" />
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-muted">
                  Step {i + 1}
                </span>
                <h3 className="mt-1 text-lg font-bold tracking-tight">{step.t}</h3>
                <p className="mt-1.5 text-sm text-terminal-muted leading-relaxed max-w-xl">{step.d}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* Stack */}
        <section className="border-t-2 border-terminal-text bg-terminal-text text-terminal-panel">
          <div className="max-w-5xl mx-auto px-5 md:px-8 py-12 md:py-14">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-terminal-accent">Stack</p>
            <h2 className="brand-mark mt-3 text-[clamp(1.75rem,4vw,2.75rem)]">
              Built to stay honest under load
              <span className="text-terminal-accent">.</span>
            </h2>
            <div className="mt-6 flex flex-wrap gap-2 font-mono text-[11px] uppercase tracking-wider">
              {[
                'React',
                'TypeScript',
                'Vite',
                'D3',
                'Recharts',
                'FastAPI',
                'SQLAlchemy',
                'APScheduler',
                'Yahoo Finance',
                'SEC EDGAR',
                'FRED',
                'OpenAI / Anthropic',
              ].map((tag) => (
                <span
                  key={tag}
                  className="border border-white/20 bg-white/5 px-3 py-1.5 text-white/75"
                >
                  {tag}
                </span>
              ))}
            </div>
            <p className="mt-6 text-sm text-white/65 max-w-2xl leading-relaxed">
              Quotes refresh on a schedule while markets are open. Filings are fetched on demand under
              EDGAR’s fair access rules. AI responses are cached by content fingerprint so the same
              filing doesn’t burn tokens twice. The Sources page lists freshness for every provider,
              including when AI is disabled and the deterministic path still runs.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row sm:items-center gap-4">
              <Link to="/map" className="btn-signal inline-flex items-center gap-2 w-fit">
                Enter the bubble map
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/data"
                className="font-mono text-[11px] uppercase tracking-[0.14em] text-white/55 hover:text-terminal-accent"
              >
                Or inspect the sources first →
              </Link>
            </div>
            <p className="mt-6 font-mono text-[11px] text-white/40">
              Not investment advice · Equities only · S&amp;P 500 universe
            </p>
          </div>
        </section>
      </main>

      <footer className="border-t-2 border-terminal-text py-4 px-5 md:px-8 font-mono text-[11px] text-terminal-muted flex flex-wrap gap-x-4 gap-y-1 justify-between max-w-5xl w-full mx-auto bg-terminal-panel">
        <span>
          Done by{' '}
          <a
            href="https://satwikmedipalli.dev"
            target="_blank"
            rel="noreferrer"
            className="text-terminal-accent underline decoration-terminal-accent/40 underline-offset-4 hover:decoration-terminal-accent"
          >
            Satwik Medipalli
          </a>
        </span>
        <span>Yahoo · SEC EDGAR · FRED</span>
      </footer>
    </div>
  );
}
