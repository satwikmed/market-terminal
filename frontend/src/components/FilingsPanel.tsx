import { useEffect, useState } from 'react';
import { api, type Filing, type FilingSection } from '../lib/api';

const SECTIONS = [
  { id: 'risk_factors', label: 'Risk Factors' },
  { id: 'mda', label: "Management's Discussion" },
  { id: 'business', label: 'Business Overview' },
];

type Props = { ticker: string };

export function FilingsPanel({ ticker }: Props) {
  const [filings, setFilings] = useState<Filing[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Filing | null>(null);
  const [section, setSection] = useState('risk_factors');
  const [raw, setRaw] = useState<FilingSection | null>(null);
  const [translation, setTranslation] = useState<string | null>(null);
  const [aiUnavailable, setAiUnavailable] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setFilings([]);
    setSelected(null);
    setRaw(null);
    setTranslation(null);
    setError(null);
    api
      .filings(ticker, 10)
      .then((r) => {
        if (!alive) return;
        setFilings(r.filings);
        setSelected(r.filings[0] ?? null);
      })
      .catch(() => alive && setError('SEC EDGAR is not responding right now.'));
    return () => {
      alive = false;
    };
  }, [ticker]);

  async function loadSection(next = section) {
    if (!selected) return;
    setBusy('raw');
    setTranslation(null);
    try {
      setRaw(await api.filingText(ticker, selected.accession, next));
    } catch {
      setRaw(null);
      setError('Could not extract that section from this filing.');
    } finally {
      setBusy(null);
    }
  }

  async function translate() {
    if (!selected) return;
    setBusy('translate');
    try {
      const r = await api.translateFiling(ticker, {
        accession: selected.accession,
        section,
        filing_type: selected.form,
      });
      setTranslation(r.translation);
      setAiUnavailable(!r.available);
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="panel-plain p-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-terminal-accent">
          SEC filings · live from EDGAR
        </h3>
        <span className="font-mono text-[10px] text-terminal-muted">
          {filings.length > 0 ? `${filings.length} most recent` : ''}
        </span>
      </div>
      <p className="text-xs text-terminal-muted mt-2">
        These are the actual documents {ticker} filed with the U.S. government. Pick one, choose a
        section, and read it raw or translated.
      </p>

      {error && <p className="mt-3 text-sm text-terminal-warn">{error}</p>}
      {!error && filings.length === 0 && (
        <p className="mt-3 text-sm text-terminal-muted">Loading filings…</p>
      )}

      <ul className="mt-3 max-h-48 overflow-auto divide-y divide-terminal-border/60">
        {filings.map((f) => {
          const active = selected?.accession === f.accession;
          return (
            <li key={f.accession}>
              <button
                type="button"
                onClick={() => {
                  setSelected(f);
                  setRaw(null);
                  setTranslation(null);
                }}
                className={`w-full text-left py-2 px-2 transition-colors ${
                  active ? 'bg-terminal-accent/10' : 'hover:bg-terminal-panel/60'
                }`}
              >
                <div className="flex items-center justify-between gap-3 font-mono text-xs">
                  <span className={active ? 'text-terminal-accent' : 'text-terminal-text'}>
                    {f.form}
                  </span>
                  <span className="text-terminal-muted tabular-nums">{f.filing_date}</span>
                </div>
                <div className="text-[11px] text-terminal-muted mt-0.5">{f.form_label}</div>
              </button>
            </li>
          );
        })}
      </ul>

      {selected && (
        <div className="mt-4 border-t border-terminal-border pt-3">
          <p className="text-sm text-terminal-muted">{selected.form_plain_english}</p>

          <div className="mt-3 flex flex-wrap gap-1">
            {SECTIONS.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => {
                  setSection(s.id);
                  setRaw(null);
                  setTranslation(null);
                }}
                className={`font-mono text-[10px] uppercase tracking-wider px-2 py-1 border ${
                  section === s.id
                    ? 'border-terminal-accent text-terminal-accent'
                    : 'border-terminal-border text-terminal-muted hover:text-terminal-text'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => loadSection()}
              className="px-3 py-2 border border-terminal-border hover:border-terminal-accent font-mono text-xs uppercase tracking-wider disabled:opacity-50"
            >
              {busy === 'raw' ? 'Fetching…' : 'Show the real text'}
            </button>
            <button
              type="button"
              disabled={busy !== null}
              onClick={translate}
              className="px-3 py-2 border border-terminal-border hover:border-terminal-accent font-mono text-xs uppercase tracking-wider disabled:opacity-50"
            >
              {busy === 'translate' ? 'Translating…' : 'Translate to plain English'}
            </button>
            <a
              href={selected.document_url}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-2 border border-terminal-border hover:border-terminal-accent font-mono text-xs uppercase tracking-wider text-terminal-muted hover:text-terminal-accent"
            >
              Open on SEC.gov ↗
            </a>
          </div>

          {translation && (
            <div className="mt-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-terminal-accent">
                {aiUnavailable ? 'AI layer not configured' : 'Plain English translation'}
              </div>
              <p className="mt-2 text-sm leading-relaxed whitespace-pre-wrap">{translation}</p>
              {!aiUnavailable && (
                <p className="mt-2 text-[10px] font-mono text-terminal-muted">
                  Translated from the filing text below — nothing added from outside the document.
                </p>
              )}
            </div>
          )}

          {raw && (
            <div className="mt-4">
              <div className="flex items-baseline justify-between gap-2">
                <div className="font-mono text-[10px] uppercase tracking-wider text-terminal-muted">
                  {raw.section_label} · {raw.form} filed {raw.filing_date}
                </div>
                <span className="font-mono text-[10px] text-terminal-muted tabular-nums">
                  {raw.characters.toLocaleString()} chars
                </span>
              </div>
              <p className="text-xs text-terminal-muted mt-1">{raw.section_plain_english}</p>
              <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap text-[12px] leading-relaxed text-terminal-muted border border-terminal-border/60 p-3 bg-terminal-bg/60">
                {raw.excerpt}
                {raw.truncated ? '\n\n[truncated — open on SEC.gov for the full section]' : ''}
              </pre>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
