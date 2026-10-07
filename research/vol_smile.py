"""Implied-vol smile from a real option-chain snapshot.

First snapshot a chain (needs network access to Yahoo Finance):

    python scripts/fetch_chain.py SPY

then run from the repo root:

    python research/vol_smile.py [data/spy_chain.csv]

Writes vol_smile.png and the "smile" section of results.json.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import numpy as np
from _common import ROOT, SERIES, plt, save, update_results

from quant.smile import Quote, build_smile

TARGET_DAYS = [30, 60, 120]


def load(chain_path: Path):
    meta = json.loads(chain_path.with_name(chain_path.stem + "_meta.json").read_text())
    as_of = datetime.fromisoformat(meta["as_of"]).date()
    by_expiry: dict[str, list[Quote]] = defaultdict(list)
    with open(chain_path) as f:
        for row in csv.DictReader(f):
            by_expiry[row["expiry"]].append(
                Quote(float(row["strike"]), row["kind"], float(row["bid"]), float(row["ask"]))
            )
    return meta, as_of, by_expiry


def main(chain_path: Path) -> None:
    meta, as_of, by_expiry = load(chain_path)
    spot = float(meta["spot"])
    days = {e: (date.fromisoformat(e) - as_of).days for e in by_expiry}
    chosen = []
    for target in TARGET_DAYS:
        best = min((e for e in by_expiry if days[e] > 0), key=lambda e: abs(days[e] - target))
        if best not in chosen:
            chosen.append(best)

    fig, ax = plt.subplots()
    summary = []
    for color, expiry in zip(SERIES, sorted(chosen), strict=False):
        T = days[expiry] / 365.0
        smile = build_smile(by_expiry[expiry], spot, T)
        pts = [p for p in smile.points if -0.3 <= p.log_moneyness <= 0.15]
        k = np.array([p.log_moneyness for p in pts])
        v = np.array([p.implied_vol for p in pts]) * 100
        ax.plot(k, v, "o-", color=color, ms=3, lw=1.5, label=f"{expiry} ({days[expiry]}d)")
        summary.append(
            {
                "expiry": expiry,
                "days": days[expiry],
                "forward": round(smile.forward, 2),
                "implied_rate": round(smile.rate, 4),
                "atm_vol": round(smile.vol_at(0.0), 4),
                "vol_90": round(smile.vol_at(np.log(0.9)), 4),
                "vol_110": round(smile.vol_at(np.log(1.1)), 4),
                "n_points": len(smile.points),
            }
        )
    ax.axvline(0, color="#898781", lw=1)
    ax.set_xlabel("Log-moneyness ln(K / F)")
    ax.set_ylabel("Implied vol (%)")
    ax.set_title(f"{meta['ticker']} implied vol smile, {as_of.isoformat()}")
    ax.legend()
    save(fig, "vol_smile.png")
    update_results(
        "smile",
        {"ticker": meta["ticker"], "spot": spot, "as_of": meta["as_of"], "source": meta["source"], "expiries": summary},
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "spy_chain.csv")
