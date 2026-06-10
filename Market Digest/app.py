"""Market Digest — on-demand report web app.

Run:
    python app.py
Then open http://127.0.0.1:5000/

Endpoints:
    GET  /             — landing page (Generate / View / Download buttons)
    POST /generate     — fetch latest data + render HTML (sync, ~10s)
    GET  /report       — the latest HTML report
    GET  /report.pdf   — PDF rendered from the latest HTML via headless Chrome
    GET  /status       — JSON status (last generated time + section coverage)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template_string, send_file, abort

from market_digest.fetch import fetch_all
from market_digest.render import render_report


BASE = Path(__file__).parent
OUTPUT = BASE / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)
REPORT_HTML = OUTPUT / "report.html"
REPORT_PDF = OUTPUT / "report.pdf"
META_FILE = OUTPUT / "meta.json"


# Find a Chrome binary at startup so /report.pdf isn't a guessing game
def _find_chrome() -> str | None:
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


CHROME_PATH = _find_chrome()


app = Flask(__name__)


# Single generate at a time — don't fire two yfinance bursts in parallel
_gen_lock = threading.Lock()


def _coverage(data: dict) -> dict:
    out = {}
    for key in ("nifty", "mmi", "constituents", "news", "fii_dii",
                "vix", "gift_nifty", "gold", "silver"):
        section = data.get(key) or {}
        out[key] = bool(section.get("available"))
    out["global"] = sum(1 for g in data["global"] if g["value"] is not None)
    out["currencies"] = sum(1 for c in data["currencies"] if c["value"] is not None)
    if data.get("sentiment"):
        out["sentiment_score"] = data["sentiment"]["score"]
        out["sentiment_label"] = data["sentiment"]["label"]
    return out


def _save_meta(data: dict) -> None:
    meta = {
        "generated_at": data["generated_at"].isoformat(),
        "coverage": _coverage(data),
    }
    META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _load_meta() -> dict | None:
    if not META_FILE.exists():
        return None
    return json.loads(META_FILE.read_text(encoding="utf-8"))


def _generate_html() -> dict:
    """Fetch data + render HTML to REPORT_HTML. Returns a status dict."""
    t0 = time.time()
    data = fetch_all()
    duration = time.time() - t0
    render_report(data, REPORT_HTML)
    _save_meta(data)
    # Invalidate any stale cached PDF
    if REPORT_PDF.exists():
        REPORT_PDF.unlink()
    return {
        "generated_at": data["generated_at"].isoformat(),
        "duration_s": round(duration, 1),
        "coverage": _coverage(data),
    }


def _render_pdf() -> Path:
    """Render the cached HTML to a PDF via headless Chrome."""
    if not REPORT_HTML.exists():
        raise FileNotFoundError("No report has been generated yet.")
    if not CHROME_PATH:
        raise RuntimeError(
            "Chrome/Edge not found. Install Chrome or set the "
            "MARKET_DIGEST_CHROME environment variable."
        )
    if REPORT_PDF.exists():
        # Reuse if the underlying HTML hasn't changed since
        if REPORT_PDF.stat().st_mtime >= REPORT_HTML.stat().st_mtime:
            return REPORT_PDF

    url = REPORT_HTML.resolve().as_uri()
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        "--hide-scrollbars",
        "--virtual-time-budget=20000",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={REPORT_PDF}",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=180)
    if result.returncode != 0 or not REPORT_PDF.exists():
        raise RuntimeError(
            f"Chrome PDF generation failed (code {result.returncode}). "
            f"stderr: {result.stderr.decode('utf-8', errors='ignore')[:400]}"
        )
    return REPORT_PDF


def _render_png(card_type: str) -> Path:
    """Render a mobile card HTML to a PNG screenshot via headless Chrome."""
    html_file = OUTPUT / f"card_{card_type}.html"
    png_file = OUTPUT / f"card_{card_type}.png"
    if not html_file.exists():
        raise FileNotFoundError(f"Card {card_type} HTML not generated yet.")
    if not CHROME_PATH:
        raise RuntimeError(
            "Chrome/Edge not found. Install Chrome or set the "
            "MARKET_DIGEST_CHROME environment variable."
        )
    if png_file.exists():
        # Reuse if the underlying HTML hasn't changed since
        if png_file.stat().st_mtime >= html_file.stat().st_mtime:
            return png_file

    url = html_file.resolve().as_uri()
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--window-size=540,1200",
        f"--screenshot={png_file}",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0 or not png_file.exists():
        raise RuntimeError(
            f"Chrome PNG generation failed (code {result.returncode}). "
            f"stderr: {result.stderr.decode('utf-8', errors='ignore')[:400]}"
        )
    return png_file



# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Market Digest — Generator</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap">
<style>
:root {
  --bg: #FBFBFD; --surface: #FFFFFF; --surface-2: #F5F5F7;
  --text: #1D1D1F; --text-2: #6E6E73; --text-3: #86868B;
  --hair: rgba(0,0,0,0.07); --shadow-sm: 0 1px 2px rgba(0,0,0,0.04), 0 4px 24px rgba(0,0,0,0.05);
  --up: #00875A; --up-soft: #E6F4EE; --down: #D70015; --down-soft: #FBE9EA;
  --accent: #0071E3;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text);
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 15px; line-height: 1.5; letter-spacing: -0.005em;
  -webkit-font-smoothing: antialiased; }
.wrap { max-width: 720px; margin: 0 auto; padding: 64px 24px; }
.brand { display: flex; align-items: center; gap: 12px; font-weight: 600;
  font-size: 17px; margin-bottom: 48px; }
.brand-mark { width: 26px; height: 26px; border-radius: 7px;
  background: linear-gradient(180deg, #1D1D1F, #3A3A3D);
  display: grid; place-items: center; }
.brand-mark::after { content: ""; width: 10px; height: 10px; border-radius: 2px;
  background: linear-gradient(135deg, #34C759 50%, #FF3B30 50%); }
h1 { font-size: 38px; font-weight: 600; letter-spacing: -0.025em;
  line-height: 1.1; margin: 0 0 8px; }
.sub { color: var(--text-2); font-size: 16px; margin: 0 0 32px; max-width: 52ch; }
.card { background: var(--surface); border: 1px solid var(--hair);
  border-radius: 16px; padding: 28px; box-shadow: var(--shadow-sm); margin-bottom: 18px; }
.row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
button, .btn { appearance: none; border: 1px solid var(--hair);
  background: var(--surface); color: var(--text);
  font: inherit; font-weight: 500; padding: 10px 18px;
  border-radius: 999px; cursor: pointer; transition: all .15s ease;
  text-decoration: none; display: inline-flex; align-items: center; gap: 8px; }
button:hover, .btn:hover { background: var(--surface-2); }
button.primary { background: var(--text); color: #fff; border-color: var(--text); }
button.primary:hover { background: #000; }
button:disabled { opacity: .5; cursor: wait; }
.status { margin-top: 16px; font-size: 13px; color: var(--text-2); }
.status .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  background: var(--text-3); margin-right: 6px; vertical-align: middle; }
.status .dot.ok { background: var(--up); box-shadow: 0 0 0 3px rgba(0,135,90,0.15); }
.status .dot.err { background: var(--down); }
.status .dot.busy { background: var(--accent); animation: pulse 1.2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.45} }

.coverage { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 6px 14px; margin-top: 14px; font-size: 12px; }
.coverage span { display: inline-flex; align-items: center; gap: 6px; color: var(--text-2); }
.coverage span::before { content:""; width: 6px; height: 6px; border-radius: 50%;
  background: var(--text-3); }
.coverage span.ok::before { background: var(--up); }
.coverage span.miss::before { background: var(--down); }
.empty { color: var(--text-3); font-size: 13px; padding: 16px 0; }
.spinner { width: 14px; height: 14px; border: 2px solid currentColor;
  border-right-color: transparent; border-radius: 50%; display: inline-block;
  animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.hint { font-size: 12px; color: var(--text-3); margin-top: 8px; }
</style>
</head>
<body>
<div class="wrap">
  <div class="brand"><span class="brand-mark"></span> Market Digest</div>

  <h1>Daily report generator</h1>
  <p class="sub">Pull the latest market data and render a printable report.
     One section per page in the PDF.</p>

  <div class="card">
    <div class="row">
      <button id="gen" class="primary">Generate today's report</button>
      <a id="view" class="btn" href="report" target="_blank" style="display:none;">View HTML →</a>
      <a id="dl" class="btn" href="report.pdf" style="display:none;">Download PDF ↓</a>
    </div>
    <div id="status" class="status">
      <span class="dot"></span>
      <span id="status-text">Loading status …</span>
    </div>
    <div id="cov-wrap" style="display:none;">
      <div class="hint" style="margin-top: 18px; font-weight: 600; color: var(--text-2);">Coverage</div>
      <div id="coverage" class="coverage"></div>
    </div>
  </div>

  <div class="hint">PDF rendering is server-side via headless Chrome. First-time PDF
     generation takes a few seconds.</div>
</div>

<script>
const $ = id => document.getElementById(id);
const SECTIONS = [
  ['nifty','NIFTY 50'], ['mmi','MMI'], ['constituents','Constituents'],
  ['news','News'], ['fii_dii','FII/DII'], ['vix','India VIX'],
  ['gift_nifty','GIFT Nifty'], ['gold','Gold'], ['silver','Silver'],
];

function setStatus(state, text) {
  $('status').innerHTML = `<span class="dot ${state}"></span><span id="status-text">${text}</span>`;
}

function renderCoverage(c) {
  if (!c) { $('cov-wrap').style.display = 'none'; return; }
  const parts = SECTIONS.map(([k,label]) => {
    const ok = c[k];
    return `<span class="${ok ? 'ok' : 'miss'}">${label}</span>`;
  });
  parts.push(`<span class="${c.global === 5 ? 'ok' : 'miss'}">Global (${c.global}/5)</span>`);
  parts.push(`<span class="${c.currencies === 6 ? 'ok' : 'miss'}">FX (${c.currencies}/6)</span>`);
  $('coverage').innerHTML = parts.join('');
  $('cov-wrap').style.display = '';
}

async function loadStatus() {
  try {
    const r = await fetch('status');
    const j = await r.json();
    if (!j.has_report) {
      setStatus('', 'No report generated yet.');
      return;
    }
    const when = new Date(j.generated_at);
    const ago = Math.round((Date.now() - when.getTime()) / 60000);
    setStatus('ok', `Last generated ${when.toLocaleString()} (${ago} min ago).`);
    $('view').style.display = '';
    $('dl').style.display = '';
    renderCoverage(j.coverage);
  } catch (e) {
    setStatus('err', 'Could not reach server.');
  }
}

$('gen').addEventListener('click', async () => {
  const btn = $('gen');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Fetching latest data …';
  setStatus('busy', 'Fetching market data (Yahoo, Moneycontrol, Tickertape, BankBazaar) — usually 10–30s.');
  try {
    const r = await fetch('generate', { method: 'POST' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const j = await r.json();
    setStatus('ok', `Generated in ${j.duration_s}s.`);
    renderCoverage(j.coverage);
    $('view').style.display = '';
    $('dl').style.display = '';
  } catch (e) {
    setStatus('err', `Generation failed: ${e.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate again';
  }
});

loadStatus();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return INDEX_HTML


@app.route("/status")
def status():
    meta = _load_meta()
    if not meta or not REPORT_HTML.exists():
        return jsonify({"has_report": False})
    return jsonify({"has_report": True, **meta})


@app.route("/generate", methods=["POST"])
def generate():
    if not _gen_lock.acquire(blocking=False):
        return jsonify({"error": "Another generation is already in progress."}), 409
    try:
        info = _generate_html()
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        _gen_lock.release()


@app.route("/report")
def report():
    if not REPORT_HTML.exists():
        abort(404, "No report generated yet — POST /generate first.")
    return send_file(REPORT_HTML, mimetype="text/html")


@app.route("/lightweight-charts.js")
def serve_lightweight_charts():
    return send_file(OUTPUT / "lightweight-charts.js", mimetype="application/javascript")


@app.route("/plotly.min.js")
def serve_plotly_min_js():
    return send_file(OUTPUT / "plotly.min.js", mimetype="application/javascript")


@app.route("/report.pdf")
def report_pdf():
    try:
        pdf = _render_pdf()
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    today = datetime.now().strftime("%Y-%m-%d")
    return send_file(
        pdf, mimetype="application/pdf",
        as_attachment=True,
        download_name=f"market-digest-{today}.pdf",
    )


@app.route("/card/indices")
def card_indices():
    html_file = OUTPUT / "card_indices.html"
    if not html_file.exists():
        abort(404, "Indices card HTML not generated yet — POST /generate first.")
    return send_file(html_file, mimetype="text/html")


@app.route("/card/news")
def card_news():
    html_file = OUTPUT / "card_news.html"
    if not html_file.exists():
        abort(404, "News card HTML not generated yet — POST /generate first.")
    return send_file(html_file, mimetype="text/html")


@app.route("/card/indices.png")
def card_indices_png():
    try:
        png = _render_png("indices")
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return send_file(png, mimetype="image/png")


@app.route("/card/news.png")
def card_news_png():
    try:
        png = _render_png("news")
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return send_file(png, mimetype="image/png")



if __name__ == "__main__":
    print(f"Market Digest web app starting …")
    print(f"  Chrome:  {CHROME_PATH or '(not found — /report.pdf will fail)'}")
    print(f"  Output:  {OUTPUT}")
    print(f"  Open:    http://127.0.0.1:5000/")
    app.run(host="127.0.0.1", port=5000, debug=False)
