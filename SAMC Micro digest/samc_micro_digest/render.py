"""Render the SAMC Micro Digest mobile card variants from fetched data."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


# ---------------------------------------------------------------------------
# Indian-style comma formatting  (e.g. 1,23,456)
# ---------------------------------------------------------------------------

def _comma_fmt(value) -> str:
    """Format an integer with Indian-style comma grouping."""
    try:
        n = int(round(float(value)))
    except (ValueError, TypeError):
        return str(value)
    if n < 0:
        return "-" + _comma_fmt(-n)
    s = str(n)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    groups: list[str] = []
    while rest:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    return ",".join(groups) + "," + last3


def _build_fmt(data: dict) -> dict:
    """Pre-format all numeric values so the template only needs {{ fmt.xxx }}."""
    mc = data.get("mobile_card") or {}
    q = mc.get("quotes") or {}
    fmt: dict[str, Any] = {}

    # Indices: value + change
    for key in ("bse", "nse", "mid", "small"):
        idx = q.get(key) or {}
        val = idx.get("value")
        chg = idx.get("change")
        fmt[f"{key}_val"] = _comma_fmt(val) if val is not None else "N/A"
        if chg is not None:
            sign = "+" if chg >= 0 else ""
            fmt[f"{key}_chg"] = f"{sign}{_comma_fmt(chg)}"
            fmt[f"{key}_cls"] = "up" if chg >= 0 else "down"
        else:
            fmt[f"{key}_chg"] = None
            fmt[f"{key}_cls"] = ""

    # FII / DII
    fii = mc.get("fii")
    dii = mc.get("dii")
    if fii is not None:
        sign = "+" if fii >= 0 else ""
        fmt["fii"] = f"INR {sign}{fii:,.2f} Cr"
        fmt["fii_cls"] = "up" if fii >= 0 else "down"
    else:
        fmt["fii"] = "N/A"
        fmt["fii_cls"] = ""

    if dii is not None:
        sign = "+" if dii >= 0 else ""
        fmt["dii"] = f"INR {sign}{dii:,.2f} Cr"
        fmt["dii_cls"] = "up" if dii >= 0 else "down"
    else:
        fmt["dii"] = "N/A"
        fmt["dii_cls"] = ""

    # Commodities / Currency
    brent = (q.get("brent") or {}).get("value")
    fmt["brent"] = f"{brent:.1f}" if brent is not None else "N/A"

    gold = (q.get("gold") or {}).get("value")
    fmt["gold"] = _comma_fmt(gold) if gold is not None else "N/A"

    silver = (q.get("silver") or {}).get("value")
    fmt["silver"] = f"{silver:.1f}" if silver is not None else "N/A"

    usdinr = (q.get("usdinr") or {}).get("value")
    fmt["usdinr"] = f"{usdinr:.3f}" if usdinr is not None else "N/A"

    # G-Sec
    gsec = mc.get("gsec") or {}
    fmt["gsec"] = f"{gsec['value']:.2f}%" if gsec.get("available") else "N/A"

    # PE
    pe = mc.get("pe") or {}
    fmt["pe"] = f"{pe['value']:.1f}x" if pe.get("available") else "N/A"

    return fmt


# ---------------------------------------------------------------------------
# Asset helpers
# ---------------------------------------------------------------------------

def get_base64_img(path: Path) -> str:
    """Read file and return it as a base64 encoded data URI, auto-detecting SVG contents."""
    if not path.exists():
        return ""
    try:
        is_svg = False
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                header = f.read(200)
                if "<svg" in header.lower():
                    is_svg = True
        except Exception:
            pass
            
        if is_svg:
            mime = "image/svg+xml"
        else:
            suffix = path.suffix.lower()
            if suffix in (".jpg", ".jpeg"):
                mime = "image/jpeg"
            elif suffix == ".png":
                mime = "image/png"
            elif suffix == ".webp":
                mime = "image/webp"
            elif suffix == ".svg":
                mime = "image/svg+xml"
            else:
                mime = "image/png"
                
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_report(data: dict[str, Any], output_dir: Path) -> None:
    import json
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load config.json
    config_path = Path(__file__).parent.parent / "config.json"
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    watermark_mode = config.get("watermark_mode", "both")
    colors = config.get("brand_colors", {})
    disclaimer_text = config.get("disclaimer_text", "Mutual Fund investments are subject to market risks, read all scheme related documents carefully.")
    
    # Generate dynamic logo base64 based on configuration settings
    company_id = config.get("active_company", "wealth")
    logo_src = Path(__file__).parent.parent / "logos" / f"{company_id}.jpeg"
    logo_base64 = ""
    if logo_src.exists():
        logo_base64 = get_base64_img(logo_src)
    else:
        # Fallback to desktop if local not found
        desktop_logo = Path("C:/Users/K964/OneDrive - Shriram Finance Limited/Desktop/logo.png")
        if desktop_logo.exists():
            logo_base64 = get_base64_img(desktop_logo)
            
    banner_src = Path(__file__).parent / "bull_bear_banner.png"
    banner_base64 = ""
    if banner_src.exists():
        banner_base64 = get_base64_img(banner_src)

    # Pre-format all numbers (no custom Jinja2 filters needed)
    fmt = _build_fmt(data)
        
    # Render Mobile Card - Indices
    card_indices_template = env.get_template("card_indices.html.j2")
    card_indices_html = card_indices_template.render(
        logo_base64=logo_base64,
        banner_base64=banner_base64,
        watermark_mode=watermark_mode,
        colors=colors,
        disclaimer_text=disclaimer_text,
        fmt=fmt,
        **data
    )
    (output_dir / "card_indices.html").write_text(card_indices_html, encoding="utf-8")
    
    # Render Mobile Card - News
    card_news_template = env.get_template("card_news.html.j2")
    card_news_html = card_news_template.render(
        logo_base64=logo_base64,
        banner_base64=banner_base64,
        watermark_mode=watermark_mode,
        colors=colors,
        disclaimer_text=disclaimer_text,
        fmt=fmt,
        **data
    )
    (output_dir / "card_news.html").write_text(card_news_html, encoding="utf-8")
