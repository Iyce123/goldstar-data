#!/usr/bin/env python3
"""Saves one snapshot of Ghana Stock Exchange prices.

Reads the free community feed (https://dev.kwayisi.org/apis/gse) and writes:
  data/latest.json            every stock: price, change, volume + company details
  data/history/<TICKER>.json  one entry per trading day: {"d","p","c","v"}

Uses only the Python standard library. Safe to run more than once a day.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE = os.environ.get("GSE_BASE", "https://dev.kwayisi.org/apis/gse").rstrip("/")
DATA_DIR = os.environ.get("DATA_DIR", "data")
TODAY = os.environ.get("SNAPSHOT_DATE") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
LATEST = os.path.join(DATA_DIR, "latest.json")
HISTORY_DIR = os.path.join(DATA_DIR, "history")


def get_json(url, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "goldstar-data/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Could not fetch {url}: {last}")


def num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def main():
    live = get_json(f"{BASE}/live")
    if not isinstance(live, list) or not live:
        sys.exit("Feed returned no stocks - nothing saved.")

    previous = read_json(LATEST, {})
    prev_by_ticker = {s["ticker"]: s for s in previous.get("stocks", []) if "ticker" in s}

    stocks = []
    for q in live:
        ticker = str(q.get("name", "")).strip()
        if not ticker:
            continue
        old = prev_by_ticker.get(ticker, {})
        try:
            p = get_json(f"{BASE}/equities/{urllib.parse.quote(ticker)}", tries=2)
        except RuntimeError:
            p = None  # keep yesterday's company details if this one fails
        company = (p or {}).get("company") or {}
        stocks.append({
            "ticker": ticker,
            "price": num(q.get("price")) or 0.0,
            "change": num(q.get("change")) or 0.0,
            "volume": int(num(q.get("volume")) or 0),
            "name": company.get("name") or old.get("name"),
            "sector": company.get("sector") or old.get("sector"),
            "industry": company.get("industry") or old.get("industry"),
            "capital": num((p or {}).get("capital")) if p else old.get("capital"),
            "eps": num((p or {}).get("eps")) if p else old.get("eps"),
            "dps": num((p or {}).get("dps")) if p else old.get("dps"),
            "shares": num((p or {}).get("shares")) if p else old.get("shares"),
        })

    # Same prices and volumes as the last save -> the market was closed, so don't record a new day.
    def fingerprint(items):
        return sorted((s["ticker"], s["price"], s["volume"]) for s in items)

    unchanged = fingerprint(stocks) == fingerprint(prev_by_ticker.values()) and bool(prev_by_ticker)
    if unchanged:
        print("Prices identical to the last save (market closed?). Nothing to do.")
        return

    write_json(LATEST, {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tradingDate": TODAY,
        "stocks": stocks,
    })

    for s in stocks:
        path = os.path.join(HISTORY_DIR, f"{s['ticker']}.json")
        rows = read_json(path, [])
        rows = [r for r in rows if r.get("d") != TODAY]  # re-running the same day replaces it
        rows.append({"d": TODAY, "p": s["price"], "c": s["change"], "v": s["volume"]})
        rows.sort(key=lambda r: r["d"])
        write_json(path, rows)

    print(f"Saved {len(stocks)} stocks for {TODAY}.")


if __name__ == "__main__":
    main()
