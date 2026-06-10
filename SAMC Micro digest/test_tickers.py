"""Test more smallcap ticker alternatives on Yahoo Finance."""
import yfinance as yf
import warnings
warnings.simplefilter("ignore")

# Extended list of possible smallcap tickers
alts = [
    "^CNXSC",               # Current - only 1 row
    "^NSMIDCP",              # NSE Smallcap
    "^CNXSML250",            # Smallcap 250
    "NIFSMCP100.NS",         # Short form
    "0P00017RKI.BO",         # BSE smallcap
]

for sym in alts:
    try:
        h = yf.Ticker(sym).history(period="5d")
        if hasattr(h, "empty") and not h.empty:
            h = h.dropna(subset=["Close"])
            n = len(h)
            if n >= 2:
                last = h["Close"].iloc[-1]
                prev = h["Close"].iloc[-2]
                chg  = last - prev
                print(f"  {sym:25s}: {n} rows | Last={last:.2f}  Prev={prev:.2f}  Chg={chg:+.2f}  ** GOOD **")
            elif n == 1:
                last = h["Close"].iloc[-1]
                print(f"  {sym:25s}: 1 row  | Last={last:.2f}")
            else:
                print(f"  {sym:25s}: EMPTY after dropna")
        else:
            print(f"  {sym:25s}: NO DATA")
    except Exception as e:
        short = str(e)[:80]
        print(f"  {sym:25s}: ERROR - {short}")

# Also try getting more days for ^CNXSC
print("\n=== ^CNXSC with longer period ===")
for period in ["5d", "10d", "1mo"]:
    try:
        h = yf.Ticker("^CNXSC").history(period=period)
        if hasattr(h, "empty") and not h.empty:
            h = h.dropna(subset=["Close"])
            print(f"  period={period:4s}: {len(h)} rows")
            if len(h) >= 2:
                print(f"    Last: {h['Close'].iloc[-1]:.2f}  Prev: {h['Close'].iloc[-2]:.2f}")
        else:
            print(f"  period={period:4s}: EMPTY")
    except Exception as e:
        print(f"  period={period:4s}: ERROR - {e}")
