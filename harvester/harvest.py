"""
Penny Stock Tracker - Hourly Data Harvester
Runs on GitHub Actions, writes JSON files to docs/data/ for the dashboard.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

# ---------- Configuration ----------

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Curated universe of liquid penny / low-priced stocks day-traders watch.
# NOT a recommendation list - just a starting universe to scan.
UNIVERSE = [
    "SNDL", "NAKD", "ZOM", "CIDM", "EXPR", "GNUS", "IDEX", "JAGX", "MARK",
    "NOK", "OCGN", "PLTR", "PROG", "SIRI", "TLRY", "XELA",
    "BBIG", "CEI", "MULN", "AMC", "GME", "NIO", "PHUN",
    "ATER", "GREE", "INDO", "HYMC", "SOS", "EBET", "RELI",
    "MMAT", "GFAI", "SNTI", "VINC", "OPK", "PLUG", "FCEL", "RIOT",
    "MARA", "BTBT", "BNGO", "CLOV", "WISH", "SOFI", "F", "GE", "T", "INTC",
    "AAL", "CCL", "NCLH", "PBR", "VALE", "ITUB", "BAC", "PFE", "AMD",
    "FUBO", "RIDE", "WKHS", "NKLA", "BLNK", "QS", "CHPT", "LCID",
]

MAX_PRICE = 10.0          # max price to include in penny scan
MIN_VOLUME = 100_000      # daily volume minimum
TIMEOUT_PER_TICKER = 15

# Keywords for catalyst classification
BULLISH_KW = [
    "fda approval", "approved", "breakthrough", "phase 3", "phase iii",
    "acquisition", "acquires", "buyout", "merger", "partnership",
    "contract awarded", "wins contract", "earnings beat", "beats estimates",
    "raises guidance", "record revenue", "all-time high", "patent granted",
    "upgrade", "price target raised", "buyback", "insider buying",
    "short squeeze", "uplisting", "uplisted", "wins lawsuit",
]
BEARISH_KW = [
    "fda rejection", "rejected", "delisting", "delisted", "bankruptcy",
    "chapter 11", "going concern", "missed estimates", "earnings miss",
    "guidance cut", "lowers guidance", "downgrade", "price target cut",
    "investigation", "sec investigation", "fraud", "class action",
    "dilution", "offering announced", "secondary offering", "reverse split",
]


# ---------- Technical analysis ----------

def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = gains[-period:].mean()
    avg_loss = losses[-period:].mean()
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def analyze_ticker(symbol):
    """Pull data and compute technical signals + score."""
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="30d", interval="1d", auto_adjust=False)
        if hist is None or len(hist) < 5:
            return None

        last_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2])
        day_change_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0

        avg_vol_20 = float(hist["Volume"].tail(20).mean()) if len(hist) >= 20 else float(hist["Volume"].mean())
        today_vol = float(hist["Volume"].iloc[-1])
        rel_volume = (today_vol / avg_vol_20) if avg_vol_20 > 0 else 0

        day_open = float(hist["Open"].iloc[-1])
        gap_pct = ((day_open - prev_close) / prev_close) * 100 if prev_close else 0

        ranges = ((hist["High"] - hist["Low"]) / hist["Close"]) * 100
        atr_pct = float(ranges.tail(14).mean())

        rsi = compute_rsi(hist["Close"].values, 14)
        ma5 = float(hist["Close"].tail(5).mean())
        ma20 = float(hist["Close"].tail(20).mean()) if len(hist) >= 20 else None

        # Scoring (heuristic, NOT a prediction)
        score = 0
        signals = []
        if rel_volume > 2:
            score += 25
            signals.append(f"Vol {rel_volume:.1f}x avg")
        elif rel_volume > 1.3:
            score += 10
        if abs(gap_pct) > 5:
            score += 15
            signals.append(f"Gap {gap_pct:+.1f}%")
        if rsi is not None:
            if rsi < 30:
                score += 15
                signals.append("Oversold")
            elif rsi > 70:
                score += 10
                signals.append("Overbought")
        if ma20 and last_close > ma20 and ma5 > ma20:
            score += 10
            signals.append("Uptrend")
        if atr_pct > 8:
            score += 10
            signals.append(f"Volatile {atr_pct:.1f}%")
        if last_close < 5:
            score += 5

        return {
            "symbol": symbol,
            "price": round(last_close, 4),
            "prev_close": round(prev_close, 4),
            "day_change_pct": round(day_change_pct, 2),
            "gap_pct": round(gap_pct, 2),
            "volume": int(today_vol),
            "avg_vol_20": int(avg_vol_20),
            "rel_volume": round(rel_volume, 2),
            "rsi": round(rsi, 1) if rsi else None,
            "atr_pct": round(atr_pct, 2),
            "ma5": round(ma5, 4),
            "ma20": round(ma20, 4) if ma20 else None,
            "score": score,
            "signals": signals,
        }
    except Exception as e:
        print(f"[scan err] {symbol}: {e}", file=sys.stderr)
        return None


def get_premarket(symbol):
    """Get pre-market quote via yfinance prepost bars."""
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="2d", interval="5m", prepost=True)
        if hist is None or len(hist) == 0:
            return None
        if hist.index.tz is None:
            hist.index = hist.index.tz_localize("UTC")
        et = hist.index.tz_convert("US/Eastern")
        dates = pd.Series(et.date)

        today = max(dates)
        yesterday_mask = dates < today
        if not yesterday_mask.any():
            return None
        prev_close = float(hist["Close"][yesterday_mask.values].iloc[-1])

        today_mask = dates == today
        today_bars = hist[today_mask.values]
        if len(today_bars) == 0:
            return None
        et_today = et[today_mask.values]
        pre_mask = [(h < 9) or (h == 9 and m < 30) for h, m in zip(et_today.hour, et_today.minute)]
        if not any(pre_mask):
            return None
        pre_bars = today_bars[pre_mask]
        if len(pre_bars) == 0:
            return None

        last_price = float(pre_bars["Close"].iloc[-1])
        pre_volume = int(pre_bars["Volume"].sum())
        gap_pct = ((last_price - prev_close) / prev_close) * 100 if prev_close else 0

        return {
            "symbol": symbol,
            "pre_price": round(last_price, 4),
            "prev_close": round(prev_close, 4),
            "gap_pct": round(gap_pct, 2),
            "pre_high": round(float(pre_bars["High"].max()), 4),
            "pre_low": round(float(pre_bars["Low"].min()), 4),
            "pre_volume": pre_volume,
        }
    except Exception as e:
        print(f"[premarket err] {symbol}: {e}", file=sys.stderr)
        return None


# ---------- News scraping ----------

def classify(title):
    t = title.lower()
    bull = [k for k in BULLISH_KW if k in t]
    bear = [k for k in BEARISH_KW if k in t]
    if bull and not bear:
        return "bullish", bull
    if bear and not bull:
        return "bearish", bear
    if bull and bear:
        return "mixed", bull + bear
    return "neutral", []


def fetch_yahoo_news(symbol, limit=5):
    try:
        t = yf.Ticker(symbol)
        items = t.news or []
        out = []
        for n in items[:limit]:
            content = n.get("content", n)
            title = content.get("title") or n.get("title", "")
            if not title:
                continue
            link = (content.get("canonicalUrl", {}) or {}).get("url") or n.get("link", "")
            publisher = (content.get("provider", {}) or {}).get("displayName") or n.get("publisher", "Yahoo")
            pub = content.get("pubDate") or n.get("providerPublishTime")
            if isinstance(pub, (int, float)):
                published = datetime.utcfromtimestamp(pub).isoformat() + "Z"
            elif isinstance(pub, str):
                published = pub
            else:
                published = None
            sentiment, kws = classify(title)
            out.append({
                "symbol": symbol, "title": title, "url": link,
                "source": publisher, "published": published,
                "sentiment": sentiment, "matched_keywords": kws,
            })
        return out
    except Exception as e:
        print(f"[yahoo news err] {symbol}: {e}", file=sys.stderr)
        return []


def fetch_finviz_news(symbol, limit=5):
    try:
        url = f"https://finviz.com/quote.ashx?t={symbol}&p=d"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", id="news-table")
        if not table:
            return []
        out, last_date = [], None
        for row in table.find_all("tr")[:limit * 2]:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            date_str = cells[0].get_text(strip=True)
            link_el = cells[1].find("a")
            if not link_el:
                continue
            title = link_el.get_text(strip=True)
            published = None
            try:
                parts = date_str.split(" ")
                if len(parts) > 1:
                    last_date = parts[0]
                    time_part = parts[1]
                else:
                    time_part = parts[0]
                if last_date:
                    dt = datetime.strptime(f"{last_date} {time_part}", "%b-%d-%y %I:%M%p")
                    published = dt.isoformat() + "Z"
            except Exception:
                pass
            sentiment, kws = classify(title)
            out.append({
                "symbol": symbol, "title": title, "url": link_el.get("href", ""),
                "source": "Finviz", "published": published,
                "sentiment": sentiment, "matched_keywords": kws,
            })
            if len(out) >= limit:
                break
        return out
    except Exception as e:
        print(f"[finviz news err] {symbol}: {e}", file=sys.stderr)
        return []


def get_news_for(symbol, limit=5):
    import re
    items = fetch_yahoo_news(symbol, limit) + fetch_finviz_news(symbol, limit)
    seen, out = set(), []
    for n in items:
        key = re.sub(r"\W+", "", n["title"].lower())[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    out.sort(key=lambda x: x.get("published") or "", reverse=True)
    return out[:limit]


# ---------- Pre-market gappers from Finviz ----------

def fetch_finviz_gainers():
    """Scrape Finviz top gainers (covers pre-market when run before open)."""
    try:
        url = "https://finviz.com/screener.ashx?v=111&s=ta_topgainers"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("tr[valign='top']")
        out = []
        for row in rows[:30]:
            cells = row.find_all("td")
            if len(cells) < 11:
                continue
            try:
                sym = cells[1].get_text(strip=True)
                price_s = cells[8].get_text(strip=True)
                chg_s = cells[9].get_text(strip=True).replace("%", "")
                vol_s = cells[10].get_text(strip=True).replace(",", "")
                if not sym or sym == "Ticker":
                    continue
                out.append({
                    "symbol": sym,
                    "price": float(price_s) if price_s.replace(".", "").replace("-", "").isdigit() else None,
                    "change_pct": float(chg_s) if chg_s.replace(".", "").replace("-", "").isdigit() else None,
                    "volume": int(vol_s) if vol_s.isdigit() else None,
                })
            except Exception:
                continue
        return out
    except Exception as e:
        print(f"[finviz gainers err]: {e}", file=sys.stderr)
        return []


# ---------- Main harvest ----------

def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str))
    print(f"  wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")


def main():
    now = datetime.now(timezone.utc)
    print(f"=== Harvest starting at {now.isoformat()} ===")

    # 1) Scan universe
    print(f"\n[1/4] Scanning {len(UNIVERSE)} tickers...")
    scan_results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(analyze_ticker, s): s for s in UNIVERSE}
        for f in as_completed(futures):
            r = f.result()
            if r and r["price"] <= MAX_PRICE and r["volume"] >= MIN_VOLUME:
                scan_results.append(r)
    scan_results.sort(key=lambda x: x["score"], reverse=True)
    print(f"  {len(scan_results)} tickers passed filters")
    write_json(DATA_DIR / "scan.json", {
        "updated": now.isoformat(),
        "count": len(scan_results),
        "filters": {"max_price": MAX_PRICE, "min_volume": MIN_VOLUME},
        "results": scan_results,
    })

    # 2) Pre-market
    print(f"\n[2/4] Pre-market gappers...")
    premarket_results = []
    # Try yfinance pre-market for top scoring tickers
    top_for_pre = [r["symbol"] for r in scan_results[:25]] + UNIVERSE[:20]
    top_for_pre = list(dict.fromkeys(top_for_pre))
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(get_premarket, s): s for s in top_for_pre}
        for f in as_completed(futures):
            r = f.result()
            if r and abs(r["gap_pct"]) >= 2:
                premarket_results.append(r)
    premarket_results.sort(key=lambda x: abs(x["gap_pct"]), reverse=True)
    finviz_movers = fetch_finviz_gainers()
    print(f"  yfinance pre: {len(premarket_results)} | finviz top gainers: {len(finviz_movers)}")
    write_json(DATA_DIR / "premarket.json", {
        "updated": now.isoformat(),
        "premarket": premarket_results,
        "top_gainers": finviz_movers,
    })

    # 3) News for top scoring tickers
    print(f"\n[3/4] News for top 15 tickers...")
    news_targets = [r["symbol"] for r in scan_results[:15]]
    all_news = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(get_news_for, s, 5): s for s in news_targets}
        for f in as_completed(futures):
            all_news.extend(f.result())
    all_news.sort(key=lambda x: x.get("published") or "", reverse=True)
    print(f"  {len(all_news)} news items total")
    write_json(DATA_DIR / "news.json", {
        "updated": now.isoformat(),
        "count": len(all_news),
        "items": all_news,
    })

    # 4) Manifest / status
    print(f"\n[4/4] Writing status manifest...")
    write_json(DATA_DIR / "status.json", {
        "updated": now.isoformat(),
        "universe_size": len(UNIVERSE),
        "scan_matches": len(scan_results),
        "premarket_movers": len(premarket_results),
        "news_items": len(all_news),
        "next_run": "every hour during market days (cron in workflow)",
    })

    print(f"\n=== Harvest complete at {datetime.now(timezone.utc).isoformat()} ===")


if __name__ == "__main__":
    main()
