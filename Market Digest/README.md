# Market Digest

Daily Indian markets HTML report, modelled on the Stonkzz daily PDF and rebuilt
from scratch with a fresh brand and live data. Twelve sections matching the
original page-by-page layout.

## Sections

| Page | Section | Source |
| --- | --- | --- |
| 1 | NIFTY 50 summary (LTP, prev close, open, volume, 52W & intraday range, candlestick + EMA-21, support/resistance, auto commentary) | Yahoo Finance (`^NSEI`) |
| 2 | Market Mood Index gauge (with week-over-week compare) + Top Gainers/Losers | Tickertape `mmi/now` + Yahoo Finance (Nifty 50 constituents) |
| 3 | Nifty Open Interest + NIFTY50 PCR | **Placeholder** — NSE option-chain feed not reachable from this host (see notes below) |
| 4 | NIFTY 50 sector heatmap + breadth/sector commentary | Yahoo Finance |
| 5 | Market Bulletin (10 headlines) + Key Stocks to Watch | Moneycontrol RSS + Yahoo Finance |
| 6 | FII/DII activity — last 7 days table + 20-day grouped bar chart | Moneycontrol `__NEXT_DATA__` JSON |
| 7 | India VIX (6-month line) + Near-52W High / Low (Nifty 50 universe) | Yahoo Finance (`^INDIAVIX`) |
| 8 | Global indices (Dow, Nasdaq, S&P 500, Hang Seng, FTSE) + 6 INR FX pairs + GIFT Nifty proxy | Yahoo Finance |
| 9 | Gold rates — Chennai 24K/22K (1g, 10g) + 10-day history + trend charts | BankBazaar |
| 10 | Silver rates — Chennai (1g, 100g, 1Kg) + 10-day history + trend chart | BankBazaar |
| 11 | Aggregate Sentiment Dashboard — Market Digest Score + 7 indicator cards | Derived from the above |
| 12 | Legal / data source disclosures | Static |

## Running it

```powershell
python generate_report.py
```

Writes `output/market-digest-YYYY-MM-DD.html`. Open in any browser — Plotly is
loaded from CDN; the rest is self-contained. Console prints a coverage summary so
silent failures are visible.

## Files

```
market_digest/
  fetch.py            # all data fetchers + sentiment aggregation
  render.py           # Jinja2 renderer
  templates/
    report.html.j2    # the 12-section template + inline CSS + Plotly init
generate_report.py    # entry point + coverage summary
output/               # generated reports land here
StonkzzReport-30Sep.pdf  # original report being modelled
```

## Notes & caveats

- **Intraday volume = 0** on runs before market close — Yahoo writes the daily
  bar volume after the session ends. Run after 4 PM IST for a populated value.
- **`TATAMOTORS.NS`** was delisted after the demerger; the fetcher skips it
  gracefully and continues.
- **GIFT Nifty** has no clean free Yahoo symbol — the report uses the spot Nifty
  close as a labelled proxy and tags this explicitly.
- **Tickertape MMI and ET Markets RSS** are fetched with `verify=False` due to
  an SSL chain issue on this host (Cloudflare intermediates not in `certifi`).
  Document and revisit if running on a host with a complete CA bundle.
- **NSE Option Chain (page 3)** is unreliable from non-Indian IPs — the public
  endpoint requires a sustained session that gets bot-blocked. Section renders
  a graceful "data unavailable" card. To enable, wire a working `nsepython`
  install or a paid feed into `fetch_option_chain` in `market_digest/fetch.py`.
- **BankBazaar scraping (Gold/Silver)** can rate-limit; the helper retries up to
  twice with a back-off. If a run fails repeatedly, wait a few minutes.
- **Moneycontrol HTML structure can change**. If FII/DII or news goes missing
  one day, inspect the page source and adjust the parser path in the relevant
  fetcher.

## Disclaimer

This tool is for personal/educational use. The generated report is not
financial advice. Data is sourced from third-party endpoints and may be
delayed, incomplete, or inaccurate. See page 12 of the generated report for
the full disclaimer.
