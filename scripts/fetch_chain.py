#!/usr/bin/env python3
"""Snapshot an option chain from Yahoo Finance into data/ for the smile study.

    pip install yfinance
    python scripts/fetch_chain.py            # SPY
    python scripts/fetch_chain.py QQQ

Writes data/<ticker>_chain.csv and data/<ticker>_chain_meta.json. Yahoo's data
is delayed and for personal/research use; check their terms before using it
for anything else.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_DAYS, MAX_DAYS = 7, 200


def main(ticker: str = "SPY") -> None:
    import yfinance as yf

    t = yf.Ticker(ticker)
    spot = float(t.history(period="1d")["Close"].iloc[-1])
    today = date.today()
    rows = []
    for expiry in t.options:
        days = (date.fromisoformat(expiry) - today).days
        if not MIN_DAYS <= days <= MAX_DAYS:
            continue
        chain = t.option_chain(expiry)
        for kind, frame in (("call", chain.calls), ("put", chain.puts)):
            for rec in frame.itertuples():
                rows.append(
                    {
                        "expiry": expiry,
                        "kind": kind,
                        "strike": float(rec.strike),
                        "bid": float(rec.bid or 0),
                        "ask": float(rec.ask or 0),
                        "volume": int(rec.volume) if rec.volume == rec.volume else 0,  # NaN check
                        "open_interest": int(rec.openInterest) if rec.openInterest == rec.openInterest else 0,
                    }
                )
    if not rows:
        sys.exit("no option quotes returned")

    out_dir = ROOT / "data"
    out_dir.mkdir(exist_ok=True)
    stem = ticker.lower() + "_chain"
    with open(out_dir / f"{stem}.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    meta = {
        "ticker": ticker.upper(),
        "spot": spot,
        "as_of": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "source": "Yahoo Finance via yfinance (delayed)",
    }
    (out_dir / f"{stem}_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"wrote {len(rows)} quotes for {ticker.upper()} (spot {spot:.2f}) to {out_dir}")


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["SPY"]))
