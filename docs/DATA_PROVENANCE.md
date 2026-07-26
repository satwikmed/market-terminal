# Data provenance and limitations

Trust is a product feature. Plain English Terminal identifies where each number
comes from, how fresh it is, and what it cannot prove.

## Market prices and fundamentals

- **Source:** Yahoo Finance quote and chart endpoints
- **Coverage:** current S&P 500 constituents only
- **Refresh behavior:** batched polling; closed markets show the latest regular
  close and an explicit session label
- **Limitations:** Yahoo is an unofficial, rate-limited source and is unsuitable
  for execution or regulatory reporting. Missing fundamental fields are shown
  as unavailable rather than replaced with estimates.

## SEC filings

- **Source:** SEC EDGAR submissions API and the filed documents themselves
- **Coverage:** all 503 constituents, mapped ticker → CIK from the SEC's own
  company index
- **Sections:** Risk Factors, Management's Discussion & Analysis, and Business
  are located by their item headings in the filing text. The extractor
  deliberately takes the *last* matching heading, because the first is usually a
  table-of-contents entry, and rejects matches too short to be a real section.
- **Rate limiting:** requests are throttled below the SEC's 10 requests/second
  fair-access ceiling and sent with a contact User-Agent, as EDGAR requires.
  Responses are cached for six hours (indexes) and 24 hours (documents).
- **Limitation:** 8-K filings and exhibits have no standard numbered items, so
  the reader falls back to the full document text and labels it as such.

## Move attribution

- **Inputs:** quotes and price history already in the database, plus SEC filings
  and calendar events within a few days of the move
- **Method:** a one-factor decomposition. The market component is the median
  move across all covered constituents; the industry component is the median
  move of same-sector peers in excess of the market; the remainder is treated as
  company-specific. Unusualness is the move divided by the stock's own trailing
  daily standard deviation.
- **Limitation:** this is an approximation, not a regression-based factor model,
  and it is displayed as such in the UI. Correlation with sector or market
  movement is not evidence of a shared cause, and a filing near a move is timing
  overlap rather than proof.

## Macroeconomic indicators

- **Source:** Federal Reserve Bank of St. Louis public FRED CSV feeds
- **Series:** CPI, unemployment, effective federal funds rate, real GDP growth,
  consumer sentiment, 10-year minus 2-year Treasury spread, and the published
  recession-probability model
- **Transformations:** CPI and basket components are converted to year-over-year
  percentage changes from index levels
- **Freshness:** each indicator includes its observation date; macro series
  update on different schedules and are not real-time

## Federal Reserve calendar

- **Source:** official Federal Reserve FOMC calendar
- **Limitation:** rate-cut/hold/hike probabilities are intentionally not shown
  without a reliable licensed futures-data source. A blank value is more honest
  than a fabricated probability.

## Ownership and insider activity

- **Source:** Yahoo Finance aggregation of institutional regulatory filings and
  insider Form 4 transactions
- **Freshness:** every result exposes the underlying report date
- **Limitation:** institutional holdings are periodic snapshots, not live
  positions. Insider transactions have many motivations and are not predictive
  signals.

## Company relationships

- **Curated edges:** known suppliers, customers, partners, and competitors
- **Generated coverage edges:** same-industry peers are connected so every
  constituent can be explored
- **Limitation:** an industry-peer edge means comparable exposure or
  competition; it does not assert a direct commercial relationship.

## AI analysis

- **Providers:** OpenAI or Anthropic, selected server-side
- **Execution:** generated only after a user requests it
- **Caching:** keyed by task, ticker/date, provider, and a fingerprint of the
  input, so a changed filing or changed evidence produces a fresh answer
- **Grounding:** the model never answers from its own knowledge. Filing
  translations receive the filing text and nothing else; move explanations
  receive the computed evidence bundle and are instructed not to introduce any
  cause absent from it. The UI shows the underlying text and evidence alongside
  the output so claims can be checked.
- **Degradation:** with no provider configured, filings and evidence still load
  and move explanations fall back to a deterministic summary. The app reports
  the AI layer as disabled rather than silently producing weaker output.
- **Safety:** reasons for price moves are framed as likely contributors, not
  proven causation.

## Educational models

The sector rate-sensitivity view is an educational historical-sensitivity
estimate. It is labeled separately from live observations and must not be
interpreted as a forecast or trading recommendation.
