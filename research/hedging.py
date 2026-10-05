"""Discrete delta hedging: how big is the error, and what drives it?

Writes hedging_error.png, hedging_vol_mismatch.png and the "hedging" section
of results.json. Run from the repo root: python research/hedging.py
"""

from __future__ import annotations

import numpy as np
from _common import MUTED, SERIES, loglog_slope, plt, save, update_results

from quant.black_scholes import greeks
from quant.hedging import simulate_hedge

S0, K, T, r, IV = 100.0, 100.0, 0.25, 0.02, 0.2
PATHS = 10_000


def frequency_study() -> dict:
    steps = [4, 8, 16, 32, 63, 126, 252, 504]
    stds = []
    for n in steps:
        h = simulate_hedge(S0, K, T, r, IV, n_steps=n, n_paths=PATHS, seed=1)
        stds.append(h.pnl.std(ddof=1))
    stds = np.array(stds)
    premium = h.premium

    fig, ax = plt.subplots()
    ax.loglog(steps, stds, "o-", color=SERIES[0], ms=5, label="std. dev. of hedged P&L")
    ax.loglog(steps, stds[0] * np.sqrt(steps[0] / np.array(steps)), "--", color=MUTED, lw=1.2, label="1/√N reference")
    ax.set_xlabel("Rebalances over the option's life")
    ax.set_ylabel("Std. dev. of final P&L ($)")
    ax.set_title("Delta-hedging error shrinks like 1/√N")
    ax.set_xticks(steps, [str(s) for s in steps])
    ax.legend()
    save(fig, "hedging_error.png")
    return {
        "steps": steps,
        "std": [round(float(s), 4) for s in stds],
        "slope": round(loglog_slope(steps, stds), 3),
        "premium": round(float(premium), 4),
        # 63 rebalances over 3 months is once per trading day.
        "daily_std_pct_of_premium": round(float(100 * stds[steps.index(63)] / premium), 1),
    }


def vol_mismatch_study() -> dict:
    out = {}
    fig, ax = plt.subplots()
    bins = np.linspace(-9, 6, 101)
    for color, rv in zip(SERIES, [0.1, 0.2, 0.3], strict=True):
        h = simulate_hedge(S0, K, T, r, IV, sigma_realized=rv, n_steps=63, n_paths=PATHS, seed=2)
        ax.hist(np.clip(h.pnl, bins[0], bins[-1]), bins=bins, histtype="step", lw=2, color=color,
                label=f"realized {rv:.0%}: mean {h.pnl.mean():+.2f}")
        out[f"{int(rv * 100)}"] = {
            "mean": round(float(h.pnl.mean()), 4),
            "std": round(float(h.pnl.std(ddof=1)), 4),
            # First-order prediction: selling vol at IV and realizing rv earns vega * (IV - rv).
            "vega_prediction": round(float(greeks(S0, K, T, r, IV)["vega"] * (IV - rv)), 4),
        }
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_xlabel("Final P&L of the hedged short option ($), daily rebalancing")
    ax.set_ylabel("Paths")
    ax.set_title("Selling at 20% implied vol: the realized vol decides who wins")
    ax.legend(loc="upper left")
    save(fig, "hedging_vol_mismatch.png")
    return out


if __name__ == "__main__":
    results = {"params": {"S": S0, "K": K, "T": T, "r": r, "implied_vol": IV, "paths": PATHS}}
    results["frequency"] = frequency_study()
    results["vol_mismatch"] = vol_mismatch_study()
    update_results("hedging", results)
