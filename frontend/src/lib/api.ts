const API_BASE = import.meta.env.VITE_API_URL ?? '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type ExplainedMetric = {
  metric: string;
  value_display: string;
  plain_english: string;
};

export type Quote = {
  ticker: string;
  price: number;
  change: number;
  change_pct: number;
  label: string;
  session_state: string;
  name?: string;
};

export type BubbleNode = {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  market_cap: number;
  change_pct: number;
  price: number;
};

export type CompanyDetail = {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  description?: string;
  market_cap?: number;
  pe_ratio?: number;
  eps?: number;
  revenue?: number;
  debt_to_equity?: number;
  dividend_yield?: number;
  price?: number;
  change?: number;
  change_pct?: number;
  quote_label?: string;
  metrics: ExplainedMetric[];
};

export type Relationship = {
  target_ticker: string;
  target_name: string;
  relationship_type: string;
  plain_english: string;
  target_sector?: string;
  target_change_pct?: number;
};

export type Filing = {
  form: string;
  form_label: string;
  form_plain_english: string;
  filing_date: string;
  report_date: string | null;
  accession: string;
  document_url: string;
  index_url: string;
  description: string;
};

export type FilingSection = {
  ticker: string;
  accession: string;
  form: string;
  form_label: string;
  filing_date: string;
  section: string;
  section_label: string;
  section_plain_english: string;
  excerpt: string;
  characters: number;
  truncated: boolean;
  source: string;
  source_url: string;
};

export type MoveEvidence = {
  kind: 'market' | 'sector' | 'volatility' | 'filing' | 'macro';
  title: string;
  detail: string;
  source: string;
  source_url: string | null;
  numbers: Record<string, string | number>;
};

export type Attribution = {
  total_pct: number;
  market_pct: number;
  sector_excess_pct: number;
  company_specific_pct: number;
  shares: { market: number; sector: number; company: number };
  dominant: 'market' | 'sector' | 'company';
  plain_english: string;
  method: string;
};

export type WhyMove = {
  ticker: string;
  change_pct: number;
  narrative: string;
  narrative_source?: 'ai' | 'deterministic';
  available?: boolean;
  provider?: string | null;
  drivers?: { title: string; explanation: string; confidence: number; hedge: string; source?: string; source_url?: string | null }[];
  evidence: MoveEvidence[];
  attribution: Attribution | null;
  methodology?: string;
};

export type SystemStatus = {
  app: string;
  server_time: string;
  market: { state: string; label: string; is_live: boolean };
  mode: string;
  initial_load?: { state: string; detail: unknown };
  sources: {
    id: string;
    label: string;
    provider: string;
    status: string;
    records: number | null;
    last_updated?: string | null;
    age_minutes?: number | null;
    notes: string;
  }[];
  database: Record<string, number>;
  scheduler: {
    enabled: boolean;
    running: boolean;
    jobs: { id: string; next_run: string | null }[];
    last_run: Record<string, { status: string; detail: unknown; at: string }>;
  };
};

export type FinancialStatements = {
  income: { revenue: (number | null)[]; gross_profit: (number | null)[]; operating_income: (number | null)[]; net_income: (number | null)[]; rnd: (number | null)[]; eps_diluted: (number | null)[] };
  balance: { total_assets: (number | null)[]; total_liabilities: (number | null)[]; total_equity: (number | null)[]; cash: (number | null)[]; long_term_debt: (number | null)[] };
  cashflow: { operating_cash_flow: (number | null)[]; capital_expenditure: (number | null)[]; free_cash_flow: (number | null)[] };
};

export type Financials = {
  ticker: string;
  company_name: string;
  fiscal_years: number[];
  latest_fiscal_year: number;
  currency: string;
  statements: FinancialStatements;
  ratios: Record<string, number | null>;
  peer_context: { sector: string; peer_count: number };
  source: string;
  source_url: string;
};

export type RiskMetrics = {
  ticker: string;
  as_of: string;
  observations: number;
  price: number;
  annualized_return_pct: number;
  annualized_volatility_pct: number;
  sharpe_ratio: number | null;
  beta: number | null;
  max_drawdown_pct: number;
  rsi_14: number | null;
  sma_50: number | null;
  sma_200: number | null;
  ma_cross: 'golden' | 'death' | null;
  week52_high: number;
  week52_low: number;
  pct_from_high: number | null;
  pct_off_low: number | null;
  risk_free_pct: number;
  benchmark: string;
};

export type LeaderboardRow = {
  ticker: string;
  name: string;
  sector: string;
  market_cap: number | null;
  change_pct: number | null;
  beta: number | null;
  volatility_pct: number;
  max_drawdown_pct: number;
  rsi_14: number | null;
  return_window_pct: number;
};

export type ScreenerRow = {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  price: number | null;
  change_pct: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  eps: number | null;
  dividend_yield_pct: number | null;
  mom_1m_pct: number | null;
  mom_3m_pct: number | null;
  mom_6m_pct: number | null;
};

export type BacktestResult = {
  start_date: string;
  end_date: string;
  trading_days: number;
  holdings: { ticker: string; weight_pct: number }[];
  metrics: {
    total_return_pct: number;
    cagr_pct: number;
    annualized_volatility_pct: number;
    sharpe_ratio: number | null;
    max_drawdown_pct: number;
    beta_vs_spy: number | null;
    benchmark_total_return_pct: number | null;
    excess_return_pct: number | null;
  };
  contributions: { ticker: string; weight_pct: number; return_pct: number; contribution_pct: number }[];
  curve: { date: string; portfolio: number; benchmark: number | null }[];
  benchmark: string;
  note: string;
};

export const api = {
  health: () => request<{ status: string; market: { label: string; is_live: boolean; state: string } }>('/api/health'),
  tape: () =>
    request<{ session_label: string; session_state: string; is_live: boolean; quotes: Quote[] }>(
      '/api/ticker/tape',
    ),
  bubble: () => request<{ nodes: BubbleNode[]; sectors: string[] }>('/api/bubble/map'),
  company: (ticker: string) => request<CompanyDetail>(`/api/companies/${ticker}`),
  history: (ticker: string) =>
    request<{ date: string; open: number; high: number; low: number; close: number; volume: number }[]>(
      `/api/companies/${ticker}/history`,
    ),
  analogy: (ticker: string) =>
    request<{ headline: string; comparisons: { label: string; value: string; sentence: string }[]; share_text: string }>(
      `/api/companies/${ticker}/analogy`,
    ),
  relationships: (ticker: string) => request<Relationship[]>(`/api/relationships/${ticker}`),
  macro: () => request<MacroDashboard>('/api/macro/dashboard'),
  rateSensitivity: () =>
    request<{ sectors: Record<string, number>; disclaimer: string }>('/api/macro/rate-sensitivity'),
  earnings: (ticker: string) =>
    request<{
      summary: string;
      cached: boolean;
      available: boolean;
      grounded: boolean;
      citation: { form: string; filing_date: string; source: string; source_url: string; section_label: string } | null;
    }>(`/api/ai/earnings/${ticker}`, { method: 'POST', body: '{}' }),
  whyMove: (ticker: string) =>
    request<WhyMove>(`/api/ai/why-move/${ticker}`, { method: 'POST', body: '{}' }),
  moveEvidence: (ticker: string) =>
    request<WhyMove>(`/api/ai/evidence/${ticker}`),
  filings: (ticker: string, limit = 10) =>
    request<{ ticker: string; company_name: string; cik: string; filings: Filing[]; source: string; source_url: string }>(
      `/api/filings/${ticker}?limit=${limit}`,
    ),
  filingText: (ticker: string, accession: string, section: string) =>
    request<FilingSection>(
      `/api/filings/${ticker}/${accession}/text?section=${encodeURIComponent(section)}`,
    ),
  translateFiling: (ticker: string, body: { filing_type?: string; accession?: string; section?: string; excerpt?: string }) =>
    request<{
      translation: string;
      cached: boolean;
      available: boolean;
      source: string;
      source_url: string | null;
      filing_date: string | null;
      section_label: string | null;
      excerpt_characters: number;
    }>(`/api/ai/filing/${ticker}`, { method: 'POST', body: JSON.stringify(body) }),
  status: () => request<SystemStatus>('/api/status'),
  weeklyBrief: () =>
    request<{ brief: string; cached: boolean; week: string; available: boolean; provider: string | null }>('/api/ai/weekly-brief', { method: 'POST', body: '{}' }),
  institutions: (ticker: string) =>
    request<{
      holders: { name: string; pct: number; shares: number; value: number; report_date: string | null; plain: string }[];
      note: string;
      source: string;
      source_url: string;
      as_of: string | null;
    }>(
      `/api/ownership/${ticker}/institutions`,
    ),
  insiders: (ticker: string) =>
    request<{
      activity: { person: string; relation: string; action: string; shares: number; date: string | null; plain: string }[];
      disclaimer: string;
      source: string;
      source_url: string;
      as_of: string | null;
    }>(
      `/api/ownership/${ticker}/insiders`,
    ),
  companies: (q?: string) =>
    request<{ ticker: string; name: string; sector: string; market_cap?: number }[]>(
      `/api/companies${q ? `?q=${encodeURIComponent(q)}` : ''}`,
    ),
  fundamentals: (ticker: string) => request<Financials>(`/api/fundamentals/${ticker}`),
  risk: (ticker: string) => request<RiskMetrics>(`/api/quant/${ticker}`),
  riskLeaderboard: () => request<{ benchmark: string; count: number; rows: LeaderboardRow[] }>('/api/quant/leaderboard'),
  correlation: (tickers: string[]) =>
    request<{ tickers: string[]; matrix: (number | null)[][]; observations: number }>(
      `/api/quant/correlation?tickers=${encodeURIComponent(tickers.join(','))}`,
    ),
  screener: () => request<{ count: number; sectors: string[]; rows: ScreenerRow[] }>('/api/screener'),
  backtest: (holdings: { ticker: string; weight: number }[]) =>
    request<BacktestResult>('/api/portfolio/backtest', {
      method: 'POST',
      body: JSON.stringify({ holdings }),
    }),
};

export type MacroDashboard = {
  indicators: {
    id: string;
    label: string;
    value: number;
    as_of: string;
    unit: string;
    plain_english: string;
    history: { date: string; value: number }[];
  }[];
  inflation_basket: { component: string; value: number }[];
  fed: {
    next_fomc: string;
    days_until: number | null;
    probabilities: { cut?: number | null; hold?: number | null; hike?: number | null };
    probabilities_available?: boolean;
    source?: string;
    source_url?: string;
    plain_english: string;
  };
  events: { date: string; title: string; category: string; plain_english: string }[];
  rate_sensitivity: Record<string, number>;
  yield_curve_note: string;
  data_sources?: {
    macro: string;
    macro_url: string;
    fomc: string;
    freshness: Record<string, string>;
    rate_sensitivity: string;
  };
};

export function formatMoney(n?: number | null): string {
  if (n == null) return '—';
  const abs = Math.abs(n);
  if (abs >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  return `$${n.toFixed(2)}`;
}

export function formatPct(n?: number | null): string {
  if (n == null) return '—';
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}
