"""Market Digest — daily report generator.

Usage:
    python generate_report.py

Writes:
    output/market-digest-YYYY-MM-DD.html
    output/card_indices.html & output/card_indices.png
    output/card_news.html & output/card_news.png
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from market_digest.fetch import fetch_all
from market_digest.render import render_report


def find_chrome() -> str | None:
    candidates = [
        os.environ.get("MARKET_DIGEST_CHROME"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("msedge"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def capture_screenshot(html_path: Path, png_path: Path) -> bool:
    chrome = find_chrome()
    if not chrome:
        print(f"  [screenshot] Chrome/Edge not found. Cannot capture {html_path.name}")
        return False
    
    # Remove stale PNG first
    if png_path.exists():
        try:
            png_path.unlink()
        except Exception:
            pass
            
    url = html_path.resolve().as_uri()
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--window-size=540,1200",
        f"--screenshot={png_path}",
        url,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=35)
        if res.returncode == 0 and png_path.exists():
            print(f"  [screenshot] Captured {png_path.name}")
            return True
        else:
            print(f"  [screenshot] Failed for {html_path.name}. code={res.returncode}")
            if res.stderr:
                print(f"  stderr: {res.stderr.decode('utf-8', errors='ignore')[:300]}")
    except Exception as e:
        print(f"  [screenshot] Error running Chrome: {e}")
    return False


def main() -> int:
    print("Market Digest — fetching latest data ...")
    t0 = time.time()
    data = fetch_all()
    print(f"  fetch complete in {time.time() - t0:.1f}s")

    # Print quick coverage summary so failures are visible
    for key in ("nifty", "mmi", "constituents", "option_chain", "news", "fii_dii",
                "vix", "gift_nifty", "gold", "silver"):
        section = data.get(key) or {}
        status = "ok" if section.get("available") else f"unavailable ({section.get('reason','?')})"
        print(f"  [{key}] {status}")
    print(f"  [global] {sum(1 for g in data['global'] if g['value'] is not None)}/{len(data['global'])} indices")
    print(f"  [currencies] {sum(1 for c in data['currencies'] if c['value'] is not None)}/{len(data['currencies'])} pairs")
    print(f"  [sentiment] score={data['sentiment']['score']}% ({data['sentiment']['label']}) "
          f"from {len(data['sentiment']['cards'])} indicators")

    output_dir = Path(__file__).parent / "output"
    out_html = output_dir / f"market-digest-{datetime.now().strftime('%Y-%m-%d')}.html"
    
    # Render PDF HTML and both Mobile HTML layouts
    render_report(data, out_html)
    print(f"\nMain PDF HTML written: {out_html}")
    
    # Save standard HTML files for screenshotting
    std_indices_html = output_dir / "card_indices.html"
    std_news_html = output_dir / "card_news.html"
    
    # Also save copy to output/report.html to ensure app.py loads correctly
    shutil.copy2(out_html, output_dir / "report.html")

    # Screenshot Mobile Cards
    capture_screenshot(std_indices_html, output_dir / "card_indices.png")
    capture_screenshot(std_news_html, output_dir / "card_news.png")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
