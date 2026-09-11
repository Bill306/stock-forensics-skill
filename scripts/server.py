#!/usr/bin/env python3
"""Forensics Web App — Search for a stock, generate an interactive forensic price chart."""

import html
import json
import math
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import yfinance as yf
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9^.=:_-]{1,32}$")


def normalize_symbol(value):
    """Return a normalized ticker that is safe for URLs and local filenames."""
    symbol = str(value or "").strip().upper()
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise ValueError("Ticker must be 1-32 characters using letters, numbers, or ^ . = : _ -")
    return symbol


def output_directory():
    """Resolve the configured output directory without trusting ticker input."""
    configured = os.environ.get("FORENSICS_OUTPUT_DIR")
    base = Path(configured).expanduser() if configured else Path.cwd() / "forensics-output"
    return base.resolve()


def chart_path(symbol):
    return output_directory() / f"{normalize_symbol(symbol)}_ForensicChart.html"


def script_json(value):
    """Serialize JSON safely for embedding inside an HTML script element."""
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def valid_number(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


@app.route("/")
def index():
    return SEARCH_HTML


@app.route("/api/search")
def search_ticker():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    if len(q) > 80:
        return jsonify({"error": "Search query is too long"}), 400
    try:
        results = []
        # Try direct ticker lookup
        t = yf.Ticker(q.upper())
        info = t.fast_info
        if hasattr(info, "last_price") and info.last_price:
            full_info = t.info
            results.append({
                "symbol": q.upper(),
                "name": full_info.get("longName") or full_info.get("shortName", q.upper()),
                "exchange": full_info.get("exchange", ""),
                "type": full_info.get("quoteType", ""),
                "currency": full_info.get("currency", ""),
                "price": round(info.last_price, 2) if info.last_price else None,
                "market_cap": full_info.get("marketCap"),
            })
        # Also try search
        search_results = yf.Search(q, max_results=8)
        for item in getattr(search_results, "quotes", []):
            sym = item.get("symbol", "")
            if sym and sym != q.upper():
                results.append({
                    "symbol": sym,
                    "name": item.get("longname") or item.get("shortname", sym),
                    "exchange": item.get("exchange", ""),
                    "type": item.get("quoteType", ""),
                    "currency": "",
                    "price": None,
                    "market_cap": None,
                })
        return jsonify(results[:10])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def generate_chart():
    data = request.get_json(silent=True) or {}
    try:
        symbol = normalize_symbol(data.get("symbol"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        t = yf.Ticker(symbol)
        info = t.info
        company_name = info.get("longName") or info.get("shortName", symbol)
        currency_symbol = {"JPY": "¥", "USD": "$", "EUR": "€", "GBP": "£",
                           "HKD": "HK$", "CNY": "¥", "KRW": "₩"}.get(
            info.get("currency", "USD"), "$")

        # Pull weekly OHLCV — max history
        hist = t.history(period="max", interval="1wk")
        if hist.empty:
            return jsonify({"error": f"No price data for {symbol}"}), 404

        price_data = []
        for date, row in hist.iterrows():
            price_data.append({
                "d": date.strftime("%Y-%m-%d"),
                "o": round(row["Open"], 2),
                "h": round(row["High"], 2),
                "l": round(row["Low"], 2),
                "c": round(row["Close"], 2),
                "v": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
            })

        # Gather events from yfinance data
        events = []

        # Earnings dates from history
        try:
            eh = t.earnings_history
            if eh is not None and not eh.empty:
                for _, row in eh.iterrows():
                    dt = row.name if hasattr(row.name, 'strftime') else None
                    if dt is None:
                        continue
                    ds = dt.strftime("%Y-%m-%d")
                    eps_act = row.get("epsActual")
                    eps_est = row.get("epsEstimate")
                    surprise = row.get("epsSurprise")
                    surprise_pct = row.get("epsSurprisePct")
                    # Find price on that date
                    px = find_price_on_date(price_data, ds)
                    if px and valid_number(eps_act):
                        has_estimate = valid_number(eps_est)
                        has_surprise = valid_number(surprise)
                        has_surprise_pct = valid_number(surprise_pct)
                        sp = f"{float(surprise_pct)*100:+.1f}%" if has_surprise_pct else ""
                        mv_dir = "up" if has_surprise_pct and float(surprise_pct) > 0 else "down" if has_surprise_pct and float(surprise_pct) < 0 else ""
                        estimate_text = f"{float(eps_est):.2f}" if has_estimate else "N/A"
                        surprise_text = f"{float(surprise):.2f}" if has_surprise else "N/A"
                        events.append({
                            "date": ds,
                            "cat": "earnings",
                            "title": f"EPS: {float(eps_act):.2f} vs {estimate_text}e" if has_estimate else f"EPS: {float(eps_act):.2f}",
                            "px": px,
                            "mv": sp,
                            "mvDir": mv_dir,
                            "desc": f"EPS actual: {float(eps_act):.2f}, estimate: {estimate_text}, surprise: {surprise_text} ({sp or 'N/A'})"
                        })
        except Exception:
            pass

        # Upgrades/downgrades
        try:
            ud = t.upgrades_downgrades
            if ud is not None and not ud.empty:
                recent = ud.tail(20)
                for dt, row in recent.iterrows():
                    ds = dt.strftime("%Y-%m-%d") if hasattr(dt, 'strftime') else str(dt)[:10]
                    px = find_price_on_date(price_data, ds)
                    if px:
                        firm = row.get("Firm", "")
                        grade = row.get("ToGrade", "")
                        from_grade = row.get("FromGrade", "")
                        action = row.get("Action", "")
                        events.append({
                            "date": ds,
                            "cat": "sellside",
                            "title": f"{firm}: {action} → {grade}",
                            "px": px,
                            "mv": "",
                            "mvDir": "",
                            "desc": f"{firm} {action.lower()} from {from_grade} to {grade}" if from_grade else f"{firm}: {grade}"
                        })
        except Exception:
            pass

        # Stock splits
        try:
            splits = t.splits
            if splits is not None and not splits.empty:
                for dt, ratio in splits.items():
                    ds = dt.strftime("%Y-%m-%d")
                    px = find_price_on_date(price_data, ds)
                    if px:
                        events.append({
                            "date": ds,
                            "cat": "corporate",
                            "title": f"Stock split {ratio:.0f}:1" if ratio > 1 else f"Reverse split 1:{1/ratio:.0f}",
                            "px": px,
                            "mv": "",
                            "mvDir": "",
                            "desc": f"Stock split ratio: {ratio}"
                        })
        except Exception:
            pass

        # Sort events by date
        events.sort(key=lambda e: e["date"])

        # Current stats
        last_px = price_data[-1]["c"] if price_data else 0
        first_px = price_data[0]["c"] if price_data else 1

        # TTM return
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        ttm_px = find_price_on_date(price_data, one_year_ago) or first_px
        ttm_return = ((last_px / ttm_px) - 1) * 100 if ttm_px else 0

        # Count by category
        cat_counts = {}
        for e in events:
            cat_counts[e["cat"]] = cat_counts.get(e["cat"], 0) + 1

        # Generate HTML from template
        html = generate_html(
            symbol=symbol,
            company_name=company_name,
            currency_symbol=currency_symbol,
            price_data=price_data,
            events=events,
            last_px=last_px,
            ttm_return=ttm_return,
            cat_counts=cat_counts,
        )

        # Save
        out_path = chart_path(symbol)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            f.write(html)

        return jsonify({
            "success": True,
            "path": str(out_path),
            "symbol": symbol,
            "name": company_name,
            "events_count": len(events),
            "price_points": len(price_data),
            "url": f"/chart/{quote(symbol, safe='')}",
        })
    except Exception as e:
        app.logger.exception("Chart generation failed for %s", symbol)
        return jsonify({"error": f"Chart generation failed: {type(e).__name__}"}), 500


@app.route("/api/price/<symbol>")
def live_price(symbol):
    """Live price data API — returns OHLCV for different ranges."""
    range_key = request.args.get("range", "1Y")
    try:
        symbol = normalize_symbol(symbol)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # Map range to yfinance period + interval
    range_map = {
        "1D":  {"period": "1d",  "interval": "5m"},
        "5D":  {"period": "5d",  "interval": "15m"},
        "1W":  {"period": "5d",  "interval": "15m"},
        "1M":  {"period": "1mo", "interval": "1h"},
        "3M":  {"period": "3mo", "interval": "1d"},
        "6M":  {"period": "6mo", "interval": "1d"},
        "1Y":  {"period": "1y",  "interval": "1wk"},
        "3Y":  {"period": "3y",  "interval": "1wk"},
        "5Y":  {"period": "5y",  "interval": "1wk"},
        "ALL": {"period": "max", "interval": "1wk"},
    }
    params = range_map.get(range_key, range_map["1Y"])

    try:
        t = yf.Ticker(symbol)
        hist = t.history(period=params["period"], interval=params["interval"])
        if hist.empty:
            return jsonify({"error": "No data"}), 404

        data = []
        for date, row in hist.iterrows():
            data.append({
                "d": date.strftime("%Y-%m-%d %H:%M") if params["interval"] in ("5m", "15m", "1h") else date.strftime("%Y-%m-%d"),
                "o": round(row["Open"], 2),
                "h": round(row["High"], 2),
                "l": round(row["Low"], 2),
                "c": round(row["Close"], 2),
                "v": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
            })

        return jsonify({
            "symbol": symbol,
            "range": range_key,
            "interval": params["interval"],
            "count": len(data),
            "data": data,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chart/<symbol>")
def view_chart(symbol):
    try:
        path = chart_path(symbol)
    except ValueError:
        return "Chart not found", 404
    if path.exists():
        return send_file(path)
    return "Chart not found", 404


def find_price_on_date(price_data, date_str):
    """Find closest price to a given date."""
    for p in price_data:
        if p["d"] >= date_str:
            return p["c"]
    if price_data:
        return price_data[-1]["c"]
    return None


def generate_html(symbol, company_name, currency_symbol, price_data, events, last_px, ttm_return, cat_counts):
    """Generate the forensic chart HTML."""
    price_json = script_json(price_data)
    events_json = script_json(events)
    safe_symbol = html.escape(str(symbol), quote=True)
    safe_company_name = html.escape(str(company_name), quote=True)
    safe_currency_symbol = html.escape(str(currency_symbol), quote=True)
    today = datetime.now().strftime("%d-%b-%Y").upper()

    earnings_count = cat_counts.get("earnings", 0)
    sellside_count = cat_counts.get("sellside", 0)
    scandal_count = cat_counts.get("scandal", 0)
    corporate_count = cat_counts.get("corporate", 0)
    narrative_count = cat_counts.get("narrative", 0)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_symbol} — Forensic Price Chart</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,400;0,500;0,700;1,400&family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg-deep: #0c1410;
    --bg-panel: #121c18;
    --bg-elev: #182521;
    --ink: #e8e4d8;
    --ink-dim: #9ca39a;
    --ink-faint: #6b726b;
    --rule: #1f2a25;
    --rule-hi: #2f3d36;
    --amber: #d4a93e;
    --amber-bright: #f2c850;
    --amber-glow: rgba(212, 169, 62, 0.15);
    --red: #d4574a;
    --red-soft: rgba(212, 87, 74, 0.12);
    --green: #7fa878;
    --green-soft: rgba(127, 168, 120, 0.12);
    --blue: #6b8fb8;
    --blue-soft: rgba(107, 143, 184, 0.12);
    --purple: #a88bb3;
    --purple-soft: rgba(168, 139, 179, 0.12);
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ height: 100%; }}
  body {{
    background: var(--bg-deep);
    color: var(--ink);
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    line-height: 1.55;
    overflow-x: hidden;
  }}
  body::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' /%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.6'/%3E%3C/svg%3E");
    opacity: 0.02;
    pointer-events: none;
    z-index: 1;
    mix-blend-mode: overlay;
  }}
  .page {{ max-width: 1600px; margin: 0 auto; padding: 32px 40px; position: relative; z-index: 2; }}

  .mast {{
    display: flex; justify-content: space-between; align-items: flex-end;
    padding-bottom: 20px; border-bottom: 1px solid var(--rule); margin-bottom: 20px; gap: 40px; flex-wrap: wrap;
  }}
  .mast-left .kicker {{
    font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--amber);
    letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 10px;
  }}
  .mast-left h1 {{
    font-family: 'Fraunces', serif; font-weight: 400; font-size: 40px;
    line-height: 1.05; letter-spacing: -0.01em;
  }}
  .mast-left h1 em {{ font-style: italic; color: var(--amber); font-weight: 300; }}
  .mast-left .sub {{
    margin-top: 6px; font-family: 'Fraunces', serif; font-style: italic;
    font-size: 15px; color: var(--ink-dim); max-width: 620px;
  }}
  .mast-right {{ display: flex; gap: 32px; font-family: 'JetBrains Mono', monospace; font-size: 11px; }}
  .stat .label {{ letter-spacing: 0.14em; text-transform: uppercase; font-size: 9px; color: var(--ink-faint); margin-bottom: 4px; }}
  .stat .val {{ font-family: 'Fraunces', serif; font-size: 22px; font-weight: 500; color: var(--ink); letter-spacing: 0; }}
  .stat.r {{ text-align: right; }}
  .stat .val.up {{ color: var(--green); }}

  .controls {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 20px; background: var(--bg-panel); border: 1px solid var(--rule);
    margin-bottom: 12px; gap: 20px; flex-wrap: wrap;
  }}
  .legend {{ display: flex; gap: 18px; flex-wrap: wrap; font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; }}
  .legend-item {{ display: flex; align-items: center; gap: 7px; color: var(--ink-dim); cursor: pointer; user-select: none; transition: opacity 0.15s; }}
  .legend-item.off {{ opacity: 0.35; }}
  .legend-dot {{ width: 9px; height: 9px; border-radius: 50%; }}
  .legend-dot.scandal {{ background: var(--red); box-shadow: 0 0 8px var(--red-soft); }}
  .legend-dot.earnings {{ background: var(--amber); box-shadow: 0 0 8px var(--amber-glow); }}
  .legend-dot.corporate {{ background: var(--green); box-shadow: 0 0 8px var(--green-soft); }}
  .legend-dot.sellside {{ background: var(--blue); box-shadow: 0 0 8px var(--blue-soft); }}
  .legend-dot.narrative {{ background: var(--purple); box-shadow: 0 0 8px var(--purple-soft); }}
  .range-selector {{ display: flex; gap: 4px; }}
  .range-btn {{
    background: transparent; border: 1px solid var(--rule-hi); color: var(--ink-dim);
    font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: 0.12em;
    text-transform: uppercase; padding: 6px 12px; cursor: pointer; border-radius: 2px; transition: all 0.15s;
  }}
  .range-btn:hover {{ color: var(--ink); border-color: var(--ink-dim); }}
  .range-btn.active {{ background: var(--amber-glow); color: var(--amber); border-color: var(--amber); }}

  .layout {{ display: grid; grid-template-columns: 1fr 380px; gap: 12px; }}
  .chart-wrap {{
    background: var(--bg-panel); border: 1px solid var(--rule);
    padding: 20px 24px 16px; position: relative; min-height: 620px;
  }}
  #chart-svg {{ width: 100%; height: 560px; display: block; }}
  #chart-svg text {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; fill: var(--ink-faint); }}
  #chart-svg .axis-label {{ font-size: 10px; fill: var(--ink-dim); }}
  #chart-svg .grid {{ stroke: var(--rule); stroke-width: 0.5; stroke-dasharray: 2 4; }}
  #chart-svg .price-area {{ fill: url(#areaGrad); }}
  #chart-svg .price-line {{ fill: none; stroke: var(--amber); stroke-width: 1.5; }}
  #chart-svg .event-line {{ stroke-dasharray: 3 3; stroke-width: 1; opacity: 0.4; }}
  #chart-svg .event-marker {{ cursor: pointer; transition: r 0.15s; }}
  #chart-svg .event-marker:hover {{ filter: brightness(1.3); }}
  #chart-svg .event-marker.active {{ filter: brightness(1.5) drop-shadow(0 0 6px currentColor); }}

  .chart-title {{
    font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--ink-faint);
    letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 12px;
    display: flex; justify-content: space-between;
  }}

  .tooltip {{
    position: absolute; padding: 10px 14px; background: rgba(12,20,16,0.95);
    border: 1px solid var(--amber); border-radius: 2px; pointer-events: none;
    opacity: 0; transition: opacity 0.15s; font-family: 'JetBrains Mono', monospace;
    font-size: 11px; z-index: 20; min-width: 160px; backdrop-filter: blur(8px);
  }}
  .tooltip.show {{ opacity: 1; }}
  .tooltip .tt-date {{ color: var(--amber); font-size: 10px; letter-spacing: 0.1em; margin-bottom: 4px; }}
  .tooltip .tt-row {{ display: flex; justify-content: space-between; gap: 16px; color: var(--ink-dim); }}
  .tooltip .tt-row strong {{ color: var(--ink); font-weight: 500; }}

  .events-panel {{
    background: var(--bg-panel); border: 1px solid var(--rule);
    display: flex; flex-direction: column; max-height: 700px;
  }}
  .ep-head {{
    padding: 16px 20px; border-bottom: 1px solid var(--rule); background: var(--bg-elev);
  }}
  .ep-head h2 {{ font-family: 'Fraunces', serif; font-size: 16px; font-weight: 500; }}
  .ep-head em {{ font-style: italic; color: var(--amber); }}
  .ep-head .sub {{
    font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--ink-faint);
    letter-spacing: 0.14em; text-transform: uppercase; margin-top: 4px;
  }}
  .ep-list {{ flex: 1; overflow-y: auto; scrollbar-width: thin; scrollbar-color: var(--rule-hi) transparent; }}
  .ev {{
    padding: 14px 20px; border-bottom: 1px solid var(--rule);
    cursor: pointer; transition: background 0.15s; position: relative;
  }}
  .ev:hover {{ background: var(--bg-elev); }}
  .ev.active {{ background: var(--bg-elev); border-left: 3px solid var(--amber); padding-left: 17px; }}
  .ev::before {{
    content: ''; position: absolute; top: 18px; left: 20px;
    width: 7px; height: 7px; border-radius: 50%;
  }}
  .ev.active::before {{ left: 17px; }}
  .ev[data-cat="scandal"]::before {{ background: var(--red); box-shadow: 0 0 8px var(--red); }}
  .ev[data-cat="earnings"]::before {{ background: var(--amber); box-shadow: 0 0 8px var(--amber); }}
  .ev[data-cat="corporate"]::before {{ background: var(--green); box-shadow: 0 0 8px var(--green); }}
  .ev[data-cat="sellside"]::before {{ background: var(--blue); box-shadow: 0 0 8px var(--blue); }}
  .ev[data-cat="narrative"]::before {{ background: var(--purple); box-shadow: 0 0 8px var(--purple); }}
  .ev-head {{ display: flex; justify-content: space-between; margin-left: 18px; margin-bottom: 3px; align-items: baseline; }}
  .ev-date {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--amber); letter-spacing: 0.08em; }}
  .ev-px {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--ink); }}
  .ev-px .mv {{ font-size: 9px; margin-left: 4px; }}
  .ev-px .mv.up {{ color: var(--green); }}
  .ev-px .mv.down {{ color: var(--red); }}
  .ev-title {{ margin-left: 18px; font-family: 'Fraunces', serif; font-size: 13px; font-weight: 500; line-height: 1.25; }}
  .ev-desc {{ margin-left: 18px; margin-top: 8px; font-size: 12px; color: var(--ink-dim); line-height: 1.5; }}

  .note-bar {{
    background: var(--bg-elev); border: 1px solid var(--rule); border-top: none;
    padding: 10px 20px; font-size: 11px; color: var(--ink-faint);
    font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em;
  }}

  .summary {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px; margin-top: 12px;
  }}
  .sum-cell {{
    background: var(--bg-panel); border: 1px solid var(--rule); padding: 16px 20px;
  }}
  .sum-cell .label {{ font-family: 'JetBrains Mono', monospace; font-size: 9px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-faint); margin-bottom: 6px; }}
  .sum-cell .val {{ font-family: 'Fraunces', serif; font-size: 24px; font-weight: 500; }}
  .sum-cell .val.amber {{ color: var(--amber); }}
  .sum-cell .val.green {{ color: var(--green); }}
  .sum-cell .val.red {{ color: var(--red); }}
  .sum-cell .val.blue {{ color: var(--blue); }}
  .sum-cell .note {{ font-size: 11px; color: var(--ink-faint); margin-top: 4px; }}

  .footnote {{
    margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--rule);
    display: flex; gap: 32px; flex-wrap: wrap;
    font-family: 'JetBrains Mono', monospace; font-size: 9px;
    color: var(--ink-faint); letter-spacing: 0.1em; text-transform: uppercase;
  }}
</style>
</head>
<body>
<div class="page">
  <div class="mast">
    <div class="mast-left">
      <div class="kicker">FORENSIC PRICE CHART</div>
      <h1>{safe_company_name} <em>({safe_symbol})</em></h1>
      <div class="sub">What moved this stock — every major catalyst mapped to price action</div>
    </div>
    <div class="mast-right">
      <div class="stat">
        <div class="label">Last Close</div>
        <div class="val" id="lastPx">{safe_currency_symbol}{last_px:,.2f}</div>
      </div>
      <div class="stat r">
        <div class="label">Period Return</div>
        <div class="val up" id="periodRet">—</div>
      </div>
    </div>
  </div>

  <div class="controls">
    <div class="legend">
      <div class="legend-item" data-cat="scandal"><div class="legend-dot scandal"></div>Scandal</div>
      <div class="legend-item" data-cat="earnings"><div class="legend-dot earnings"></div>Earnings</div>
      <div class="legend-item" data-cat="corporate"><div class="legend-dot corporate"></div>Corporate</div>
      <div class="legend-item" data-cat="sellside"><div class="legend-dot sellside"></div>Sell-side</div>
      <div class="legend-item" data-cat="narrative"><div class="legend-dot narrative"></div>Narrative</div>
    </div>
    <div class="range-selector">
      <button class="range-btn" data-r="1D">1D</button>
      <button class="range-btn" data-r="5D">5D</button>
      <button class="range-btn" data-r="1M">1M</button>
      <button class="range-btn" data-r="3M">3M</button>
      <button class="range-btn" data-r="6M">6M</button>
      <button class="range-btn" data-r="1Y">1Y</button>
      <button class="range-btn" data-r="3Y">3Y</button>
      <button class="range-btn" data-r="5Y">5Y</button>
      <button class="range-btn active" data-r="ALL">All</button>
    </div>
  </div>

  <div class="layout">
    <div class="chart-wrap">
      <div class="chart-title">
        <span>WEEKLY CLOSE · {currency_symbol}</span>
        <span id="evCount">{len(events)}</span> events mapped
      </div>
      <svg id="chart-svg" viewBox="0 0 1100 560" preserveAspectRatio="xMidYMid meet"></svg>
      <div class="tooltip" id="tooltip"></div>
    </div>
    <div class="events-panel">
      <div class="ep-head">
        <h2>Catalyst <em>Dossier</em></h2>
        <div class="sub">{len(events)} events · {price_data[0]["d"][:4]}–{price_data[-1]["d"][:4]}</div>
      </div>
      <div class="ep-list" id="ev-list"></div>
    </div>
  </div>

  <div class="note-bar">
    Note: Events auto-populated from Yahoo Finance (earnings, upgrades, splits). For a complete forensic analysis, add scandal, narrative, and corporate events manually or via Claude.
  </div>

  <div class="summary">
    <div class="sum-cell">
      <div class="label">Total Events</div>
      <div class="val amber">{len(events)}</div>
      <div class="note">Auto-detected from yfinance data</div>
    </div>
    <div class="sum-cell">
      <div class="label">TTM Return</div>
      <div class="val {'green' if ttm_return >= 0 else 'red'}">{ttm_return:+.0f}%</div>
      <div class="note">Trailing 12-month</div>
    </div>
    <div class="sum-cell">
      <div class="label">Earnings Events</div>
      <div class="val amber">{earnings_count}</div>
      <div class="note">EPS surprises tracked</div>
    </div>
    <div class="sum-cell">
      <div class="label">Sell-side Events</div>
      <div class="val blue">{sellside_count}</div>
      <div class="note">Upgrades / downgrades</div>
    </div>
  </div>

  <div class="footnote">
    <span>PRICE DATA · YAHOO FINANCE</span>
    <span>EVENT ATTRIBUTION · YFINANCE + MANUAL RESEARCH</span>
    <span>PREPARED {today} · FORENSICS SKILL</span>
  </div>
</div>

<script>
const priceData = {price_json};
const events = {events_json};

const catColor = {{
  scandal: '#d4574a', earnings: '#d4a93e', corporate: '#7fa878',
  sellside: '#6b8fb8', narrative: '#a88bb3'
}};

const SYMBOL = '{symbol}';
const svg = document.getElementById('chart-svg');
const W = 1100, H = 560;
const M = {{ top: 30, right: 60, bottom: 50, left: 60 }};
let currentRange = 'ALL';
let hiddenCats = new Set();
let activeEventIdx = null;
let liveData = null;  // holds fetched live data for non-ALL ranges
let isFetching = false;

function escapeHtml(value) {{
  return String(value ?? '').replace(/[&<>"']/g, ch => ({{
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }})[ch]);
}}

function parseDate(s) {{ return new Date(s.includes('T') ? s : s + 'T00:00:00'); }}

function filterByRange(data, range) {{
  if (range === 'ALL') return data;
  const last = parseDate(data[data.length - 1].d);
  const years = {{ '1Y': 1, '3Y': 3, '5Y': 5 }}[range];
  if (!years) return data;
  const cutoff = new Date(last.getTime() - years * 365.25 * 86400000);
  return data.filter(p => parseDate(p.d) >= cutoff);
}}

async function fetchLiveData(range) {{
  if (isFetching) return;
  isFetching = true;
  const chartTitle = document.querySelector('.chart-title span');
  const origText = chartTitle.textContent;
  chartTitle.textContent = 'LOADING...';
  try {{
    const r = await fetch('/api/price/' + SYMBOL + '?range=' + range);
    const json = await r.json();
    if (json.data && json.data.length > 0) {{
      liveData = json.data;
      const intervalLabel = json.interval || '';
      chartTitle.textContent = intervalLabel.toUpperCase() + ' CLOSE · {currency_symbol}';
      render();
    }} else {{
      chartTitle.textContent = origText;
    }}
  }} catch (e) {{
    chartTitle.textContent = origText;
    console.error('Failed to fetch live data:', e);
  }} finally {{
    isFetching = false;
  }}
}}

function render() {{
  const useLocal = ['ALL', '1Y', '3Y', '5Y'].includes(currentRange);
  const data = liveData && !useLocal ? liveData : filterByRange(priceData, currentRange);
  const visibleEvents = events
    .map((e, i) => ({{ ...e, idx: i }}))
    .filter(e => !hiddenCats.has(e.cat))
    .filter(e => {{
      const d = parseDate(e.date);
      return d >= parseDate(data[0].d) && d <= parseDate(data[data.length - 1].d);
    }});

  svg.innerHTML = '';
  let minP = Infinity, maxP = -Infinity;
  data.forEach(p => {{ minP = Math.min(minP, p.l); maxP = Math.max(maxP, p.h); }});
  const padP = (maxP - minP) * 0.08;
  minP = Math.max(0, minP - padP);
  maxP = maxP + padP;

  const startT = parseDate(data[0].d).getTime();
  const endT = parseDate(data[data.length - 1].d).getTime();
  const xScale = t => M.left + ((t - startT) / (endT - startT)) * (W - M.left - M.right);
  const yScale = p => M.top + ((maxP - p) / (maxP - minP)) * (H - M.top - M.bottom);

  const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
  defs.innerHTML = `<linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#d4a93e" stop-opacity="0.25"/><stop offset="100%" stop-color="#d4a93e" stop-opacity="0"/></linearGradient>`;
  svg.appendChild(defs);

  // Y grid
  const niceTicks = (min, max, count = 6) => {{
    const range = max - min; const rough = range / count;
    const mag = Math.pow(10, Math.floor(Math.log10(rough)));
    const norm = rough / mag;
    let step;
    if (norm < 1.5) step = 1 * mag; else if (norm < 3) step = 2 * mag;
    else if (norm < 7) step = 5 * mag; else step = 10 * mag;
    const ticks = []; const first = Math.ceil(min / step) * step;
    for (let v = first; v <= max; v += step) ticks.push(v);
    return ticks;
  }};

  niceTicks(minP, maxP).forEach(p => {{
    const y = yScale(p);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', M.left); line.setAttribute('x2', W - M.right);
    line.setAttribute('y1', y); line.setAttribute('y2', y);
    line.setAttribute('class', 'grid');
    svg.appendChild(line);
    const lbl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    lbl.setAttribute('x', W - M.right + 6); lbl.setAttribute('y', y + 3);
    lbl.setAttribute('class', 'axis-label');
    lbl.textContent = '{currency_symbol}' + Math.round(p).toLocaleString();
    svg.appendChild(lbl);
  }});

  // Year ticks
  const years = new Set();
  data.forEach(p => years.add(p.d.slice(0, 4)));
  [...years].sort().forEach(yr => {{
    const firstInYr = data.find(p => p.d.startsWith(yr));
    if (!firstInYr) return;
    const x = xScale(parseDate(firstInYr.d).getTime());
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', x); line.setAttribute('x2', x);
    line.setAttribute('y1', H - M.bottom); line.setAttribute('y2', H - M.bottom + 5);
    line.setAttribute('class', 'year-tick');
    line.setAttribute('stroke', '#2f3d36');
    svg.appendChild(line);
    const lbl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    lbl.setAttribute('x', x); lbl.setAttribute('y', H - M.bottom + 18);
    lbl.setAttribute('text-anchor', 'middle'); lbl.setAttribute('class', 'axis-label');
    lbl.textContent = yr;
    svg.appendChild(lbl);
  }});

  // Price area + line
  let areaPath = '', linePath = '';
  data.forEach((p, i) => {{
    const x = xScale(parseDate(p.d).getTime());
    const y = yScale(p.c);
    linePath += (i === 0 ? 'M' : 'L') + x + ',' + y;
    areaPath += (i === 0 ? 'M' : 'L') + x + ',' + y;
  }});
  areaPath += `L${{xScale(parseDate(data[data.length-1].d).getTime())}},${{H-M.bottom}} L${{xScale(parseDate(data[0].d).getTime())}},${{H-M.bottom}} Z`;

  const area = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  area.setAttribute('d', areaPath); area.setAttribute('class', 'price-area');
  svg.appendChild(area);
  const priceLine = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  priceLine.setAttribute('d', linePath); priceLine.setAttribute('class', 'price-line');
  svg.appendChild(priceLine);

  // Event markers
  visibleEvents.forEach(e => {{
    const t = parseDate(e.date).getTime();
    const x = xScale(t); const y = yScale(e.px);
    const vline = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    vline.setAttribute('x1', x); vline.setAttribute('x2', x);
    vline.setAttribute('y1', M.top); vline.setAttribute('y2', y);
    vline.setAttribute('class', 'event-line');
    vline.setAttribute('stroke', catColor[e.cat]);
    svg.appendChild(vline);

    const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    dot.setAttribute('cx', x); dot.setAttribute('cy', y);
    dot.setAttribute('r', activeEventIdx === e.idx ? 8 : 5.5);
    dot.setAttribute('fill', catColor[e.cat]);
    dot.setAttribute('stroke', '#0c1410'); dot.setAttribute('stroke-width', '2');
    dot.setAttribute('class', 'event-marker' + (activeEventIdx === e.idx ? ' active' : ''));
    dot.addEventListener('click', (ev) => {{ ev.stopPropagation(); setActiveEvent(e.idx, true); }});
    dot.addEventListener('mouseenter', (ev) => showEventTooltip(e, ev));
    dot.addEventListener('mouseleave', hideTooltip);
    svg.appendChild(dot);

    // Numbered tag
    const tag = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    tag.setAttribute('transform', `translate(${{x}}, ${{y - 14}})`);
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bg.setAttribute('x', -9); bg.setAttribute('y', -11);
    bg.setAttribute('width', 18); bg.setAttribute('height', 14); bg.setAttribute('rx', 2);
    bg.setAttribute('fill', '#0c1410'); bg.setAttribute('stroke', catColor[e.cat]); bg.setAttribute('stroke-width', '1');
    const num = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    num.setAttribute('x', 0); num.setAttribute('y', 0);
    num.setAttribute('text-anchor', 'middle'); num.setAttribute('font-size', '9');
    num.setAttribute('font-weight', '600'); num.setAttribute('fill', catColor[e.cat]);
    num.setAttribute('font-family', 'JetBrains Mono, monospace');
    num.textContent = e.idx + 1;
    tag.appendChild(bg); tag.appendChild(num);
    tag.style.cursor = 'pointer';
    tag.addEventListener('click', () => setActiveEvent(e.idx, true));
    svg.appendChild(tag);
  }});

  // Stats
  const lastPx = data[data.length - 1].c;
  const firstPx = data[0].c;
  const ret = ((lastPx / firstPx) - 1) * 100;
  const retEl = document.getElementById('periodRet');
  retEl.textContent = (ret >= 0 ? '+' : '') + ret.toFixed(1) + '%';
  retEl.style.color = ret >= 0 ? 'var(--green)' : 'var(--red)';
  document.getElementById('evCount').textContent = visibleEvents.length;
}}

function renderEventList() {{
  const listEl = document.getElementById('ev-list');
  listEl.innerHTML = '';
  const sorted = events.map((e, i) => ({{ ...e, idx: i }})).reverse();
  sorted.forEach(e => {{
    const el = document.createElement('div');
    el.className = 'ev' + (activeEventIdx === e.idx ? ' active' : '');
    el.dataset.cat = e.cat; el.dataset.idx = e.idx;
    const moveClass = e.mvDir === 'up' || e.mvDir === 'down' ? e.mvDir : '';
    const mvHtml = e.mv ? `<span class="mv ${{moveClass}}">${{escapeHtml(e.mv)}}</span>` : '';
    el.innerHTML = `
      <div class="ev-head">
        <span class="ev-date">${{String(e.idx + 1).padStart(2, '0')}} · ${{escapeHtml(e.date)}}</span>
        <span class="ev-px">{currency_symbol}${{e.px.toLocaleString()}}${{mvHtml}}</span>
      </div>
      <div class="ev-title">${{escapeHtml(e.title)}}</div>
      <div class="ev-desc">${{escapeHtml(e.desc)}}</div>
    `;
    el.addEventListener('click', () => setActiveEvent(e.idx, false));
    listEl.appendChild(el);
  }});
}}

function setActiveEvent(idx, scrollList) {{
  activeEventIdx = idx; renderEventList(); render();
  if (scrollList) {{
    const el = document.querySelector(`.ev[data-idx="${{idx}}"]`);
    if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
  }}
}}

const tooltip = document.getElementById('tooltip');
function showEventTooltip(e, mouseEv) {{
  const wrapRect = document.querySelector('.chart-wrap').getBoundingClientRect();
  const mvHtml = e.mv ? `<div class="tt-row"><span>Move</span><strong style="color:${{e.mvDir==='up'?'var(--green)':e.mvDir==='down'?'var(--red)':'var(--ink)'}}">${{escapeHtml(e.mv)}}</strong></div>` : '';
  tooltip.innerHTML = `<div class="tt-date">${{escapeHtml(e.date)}}</div><div class="tt-row"><span>Price</span><strong>{currency_symbol}${{e.px.toLocaleString()}}</strong></div>${{mvHtml}}<div style="margin-top:6px;color:var(--ink);font-size:10px">${{escapeHtml(e.title)}}</div>`;
  tooltip.style.left = (mouseEv.clientX - wrapRect.left + 16) + 'px';
  tooltip.style.top = (mouseEv.clientY - wrapRect.top - 40) + 'px';
  tooltip.classList.add('show');
}}
function hideTooltip() {{ tooltip.classList.remove('show'); }}

// Legend toggles
document.querySelectorAll('.legend-item').forEach(item => {{
  item.addEventListener('click', () => {{
    const cat = item.dataset.cat;
    if (hiddenCats.has(cat)) {{ hiddenCats.delete(cat); item.classList.remove('off'); }}
    else {{ hiddenCats.add(cat); item.classList.add('off'); }}
    render();
  }});
}});

// Range selector — fetch live data for short ranges, use embedded data for long ranges
document.querySelectorAll('.range-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentRange = btn.dataset.r;
    const useLocal = ['ALL', '1Y', '3Y', '5Y'].includes(currentRange);
    if (useLocal) {{
      liveData = null;
      document.querySelector('.chart-title span').textContent = 'WEEKLY CLOSE · {currency_symbol}';
      render();
    }} else {{
      fetchLiveData(currentRange);
    }}
  }});
}});

renderEventList();
render();
</script>
</body>
</html>'''


# ============================================================
# SEARCH PAGE HTML
# ============================================================
SEARCH_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Forensics — Stock Search</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,400;0,500;0,700;1,400&family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-deep: #0c1410; --bg-panel: #121c18; --bg-elev: #182521;
    --ink: #e8e4d8; --ink-dim: #9ca39a; --ink-faint: #6b726b;
    --rule: #1f2a25; --rule-hi: #2f3d36;
    --amber: #d4a93e; --amber-bright: #f2c850; --amber-glow: rgba(212,169,62,0.15);
    --green: #7fa878; --red: #d4574a;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--bg-deep); color: var(--ink);
    font-family: 'Inter', sans-serif; min-height: 100vh;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
  }
  .container { max-width: 680px; width: 90%; padding: 40px 0; }
  .kicker {
    font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--amber);
    letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 12px; text-align: center;
  }
  h1 {
    font-family: 'Fraunces', serif; font-weight: 400; font-size: 48px;
    text-align: center; margin-bottom: 8px; letter-spacing: -0.02em;
  }
  h1 em { font-style: italic; color: var(--amber); font-weight: 300; }
  .sub {
    text-align: center; font-family: 'Fraunces', serif; font-style: italic;
    font-size: 16px; color: var(--ink-dim); margin-bottom: 40px;
  }
  .search-box {
    display: flex; gap: 8px; margin-bottom: 16px;
  }
  .search-box input {
    flex: 1; padding: 16px 24px; background: var(--bg-panel);
    border: 1px solid var(--rule-hi); border-radius: 4px;
    color: var(--ink); font-size: 18px; font-family: 'Inter', sans-serif;
    outline: none; transition: border 0.2s;
  }
  .search-box input:focus { border-color: var(--amber); }
  .search-box input::placeholder { color: var(--ink-faint); }
  .search-box button {
    padding: 16px 28px; background: var(--amber); color: #0c1410;
    border: none; border-radius: 4px; font-family: 'JetBrains Mono', monospace;
    font-size: 12px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    cursor: pointer; transition: opacity 0.15s;
  }
  .search-box button:hover { opacity: 0.85; }

  .results { list-style: none; }
  .results li {
    padding: 16px 20px; background: var(--bg-panel); border: 1px solid var(--rule);
    margin-bottom: 6px; cursor: pointer; transition: all 0.15s; display: flex;
    justify-content: space-between; align-items: center;
  }
  .results li:hover { border-color: var(--amber); background: var(--bg-elev); }
  .results li .sym {
    font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 600;
    color: var(--amber); min-width: 100px;
  }
  .results li .name { flex: 1; font-size: 14px; color: var(--ink); margin-left: 16px; }
  .results li .meta {
    font-family: 'JetBrains Mono', monospace; font-size: 11px;
    color: var(--ink-faint); text-align: right;
  }

  .loading { text-align: center; padding: 40px; color: var(--ink-faint); display: none; }
  .loading.show { display: block; }
  .loading .spinner {
    width: 24px; height: 24px; border: 2px solid var(--rule-hi);
    border-top-color: var(--amber); border-radius: 50%;
    animation: spin 0.8s linear infinite; margin: 0 auto 12px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .gen-status {
    text-align: center; padding: 40px; display: none;
  }
  .gen-status.show { display: block; }
  .gen-status .big {
    font-family: 'Fraunces', serif; font-size: 22px; margin-bottom: 8px;
  }
  .gen-status .detail { font-size: 13px; color: var(--ink-dim); }
  .gen-status a {
    display: inline-block; margin-top: 16px; padding: 12px 24px;
    background: var(--amber); color: #0c1410; text-decoration: none;
    font-family: 'JetBrains Mono', monospace; font-size: 12px;
    font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    border-radius: 4px;
  }

  .tip {
    text-align: center; margin-top: 32px; font-size: 12px; color: var(--ink-faint);
    font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em;
  }
</style>
</head>
<body>
<div class="container">
  <div class="kicker">FORENSIC ANALYSIS</div>
  <h1>Know the <em>Stock</em></h1>
  <div class="sub">What moved the price? Search for any stock to generate an interactive forensic chart.</div>

  <div class="search-box">
    <input type="text" id="q" placeholder="Enter ticker or company name..." autofocus>
    <button onclick="doSearch()">Search</button>
  </div>

  <ul class="results" id="results"></ul>

  <div class="loading" id="loading">
    <div class="spinner"></div>
    <div>Searching...</div>
  </div>

  <div class="gen-status" id="genStatus">
    <div class="spinner" style="border:2px solid #2f3d36;border-top-color:#d4a93e;border-radius:50%;width:32px;height:32px;animation:spin 0.8s linear infinite;margin:0 auto 16px"></div>
    <div class="big">Generating forensic chart...</div>
    <div class="detail" id="genDetail">Pulling price data and events from Yahoo Finance</div>
  </div>

  <div class="tip">
    Try: AAPL, 3563.T, TSMC, 700.HK, SAP, MC.PA
  </div>
</div>

<script>
let timer;
const input = document.getElementById('q');
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[ch]);
}
input.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
input.addEventListener('input', () => {
  clearTimeout(timer);
  timer = setTimeout(doSearch, 400);
});

async function doSearch() {
  const q = input.value.trim();
  if (!q) return;
  document.getElementById('loading').classList.add('show');
  document.getElementById('results').innerHTML = '';
  try {
    const r = await fetch('/api/search?q=' + encodeURIComponent(q));
    const data = await r.json();
    document.getElementById('loading').classList.remove('show');
    if (data.error) { alert(data.error); return; }
    const ul = document.getElementById('results');
    ul.innerHTML = '';
    data.forEach(item => {
      const li = document.createElement('li');
      li.innerHTML = `
        <span class="sym">${escapeHtml(item.symbol)}</span>
        <span class="name">${escapeHtml(item.name)}</span>
        <span class="meta">${escapeHtml(item.exchange || '')}<br>${item.price ? escapeHtml(item.price.toLocaleString()) : ''}</span>
      `;
      li.addEventListener('click', () => generateChart(item.symbol, item.name));
      ul.appendChild(li);
    });
  } catch (e) {
    document.getElementById('loading').classList.remove('show');
    alert('Search failed: ' + e.message);
  }
}

async function generateChart(symbol, name) {
  document.getElementById('results').innerHTML = '';
  const gen = document.getElementById('genStatus');
  gen.classList.add('show');
  document.getElementById('genDetail').textContent = `Pulling data for ${symbol} (${name})...`;
  try {
    const r = await fetch('/api/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({symbol})
    });
    const data = await r.json();
    if (data.error) {
      gen.innerHTML = `<div class="big" style="color:var(--red)">Error</div><div class="detail">${escapeHtml(data.error)}</div>`;
      return;
    }
    gen.innerHTML = `
      <div class="big" style="color:var(--green)">Chart Ready</div>
      <div class="detail">${escapeHtml(data.name)} — ${escapeHtml(data.price_points)} price points, ${escapeHtml(data.events_count)} events</div>
      <a href="${escapeHtml(data.url)}" target="_blank" rel="noopener noreferrer">Open Forensic Chart</a>
      <div style="margin-top:12px;font-size:11px;color:var(--ink-faint)">
        Also saved to: ${escapeHtml(data.path)}
      </div>
    `;
  } catch (e) {
    gen.innerHTML = `<div class="big" style="color:var(--red)">Error</div><div class="detail">${e.message}</div>`;
  }
}
</script>
</body>
</html>'''


if __name__ == "__main__":
    host = os.environ.get("FORENSICS_HOST", "127.0.0.1")
    port = int(os.environ.get("FORENSICS_PORT", "3457"))
    print(f"\nForensics Web App running at http://{host}:{port}\n")
    app.run(host=host, port=port, debug=False, threaded=True)
