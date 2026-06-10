"""SAMC Micro Digest — card infographics generator.

Usage:
    python generate_report.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from samc_micro_digest.fetch import fetch_all
from samc_micro_digest.render import render_report


def find_chrome() -> str | None:
    candidates = [
        os.environ.get("SAMC_MICRO_DIGEST_CHROME"),
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
    except Exception as e:
        print(f"  [screenshot] Error running Chrome: {e}")
    return False


def main() -> int:
    print("SAMC Micro Digest — fetching latest data ...")
    t0 = time.time()
    data = fetch_all()
    print(f"  fetch complete in {time.time() - t0:.1f}s")

    output_dir = Path(__file__).parent / "output"
    outputs_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    # Render both Mobile HTML layouts
    render_report(data, output_dir)
    print(f"HTML layouts generated under output/")
    
    # Screenshot Mobile Cards
    capture_screenshot(output_dir / "card_indices.html", output_dir / "card_indices.png")
    capture_screenshot(output_dir / "card_news.html", output_dir / "card_news.png")
    
    # Sync to outputs directory
    try:
        shutil.copy2(output_dir / "card_indices.png", outputs_dir / "card_indices.png")
        shutil.copy2(output_dir / "card_news.png", outputs_dir / "card_news.png")
        shutil.copy2(output_dir / "card_indices.html", outputs_dir / "card_indices.html")
        shutil.copy2(output_dir / "card_news.html", outputs_dir / "card_news.html")
        print("Synchronized generated files to outputs/ directory.")
    except Exception as e:
        print(f"Warning: Failed to copy to outputs/ directory: {e}")
        
    # Copy to Desktop if available
    desktop = Path(r"C:\Users\K964\OneDrive - Shriram Finance Limited\Desktop")
    if not desktop.exists():
        desktop = Path(r"C:\Users\K964\Desktop")
    if desktop.exists():
        try:
            shutil.copy2(output_dir / "card_indices.png", desktop / "card_indices.png")
            shutil.copy2(output_dir / "card_news.png", desktop / "card_news.png")
            print(f"Successfully copied card PNGs to Desktop: {desktop}")
        except Exception as e:
            print(f"Warning: Failed to copy to Desktop: {e}")
            
    return 0


if __name__ == "__main__":
    sys.exit(main())
