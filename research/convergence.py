"""How fast do the binomial tree and Monte Carlo converge to Black-Scholes?

Writes convergence_crr.png, convergence_mc.png and the "convergence" section
of results.json. Run from the repo root: python research/convergence.py
"""

from __future__ import annotations

import numpy as np
from _common import INK_2, MUTED, SERIES, loglog_slope, plt, save, update_results

from quant.binomial import crr_price
from quant.black_scholes import price
from quant.monte_carlo import mc_price

S, K, T, r, sigma = 100.0, 105.0, 1.0, 0.05, 0.2


def crr_study() -> dict:
    bs = price(S, K, T, r, sigma)
    steps = np.unique(np.round(np.logspace(1, 3.3, 60)).astype(int))
    errors = np.array([abs(crr_price(S, K, T, r, sigma, steps=int(n)) - bs) for n in steps])
    odd = steps % 2 == 1

    fig, ax = plt.subplots()
    ax.loglog(steps[~odd], errors[~odd], "o-", color=SERIES[0], ms=4, label="even step counts")
    ax.loglog(steps[odd], errors[odd], "o-", color=SERIES[1], ms=4, label="odd step counts")
    ref = errors[0] * steps[0] / steps
    ax.loglog(steps, ref, "--", color=MUTED, lw=1.2, label="1/N reference")
    ax.set_xlabel("Tree steps N")
    ax.set_ylabel("|CRR − Black-Scholes|")
    ax.set_title("Binomial tree error falls like 1/N, but not smoothly")
    ax.legend()
    save(fig, "convergence_crr.png")

    slope = loglog_slope(steps, errors)
    amer = crr_price(S, K, T, r, sigma, kind="put", steps=2000, american=True)
    euro = price(S, K, T, r, sigma, kind="put")
    return {
        "crr_slope": round(slope, 3),
        "crr_error_at_1000": float(errors[np.argmin(abs(steps - 1000))]),
        "american_put": round(amer, 4),
        "european_put": round(euro, 4),
        "early_exercise_premium": round(amer - euro, 4),
    }


def mc_study() -> dict:
    bs = price(S, K, T, r, sigma)
    paths = np.unique(np.round(np.logspace(3, 6, 13)).astype(int))
    variants = [
        ("plain", dict(antithetic=False, control_variate=False)),
        ("antithetic", dict(antithetic=True, control_variate=False)),
        ("antithetic + control variate", dict(antithetic=True, control_variate=True)),
    ]
    out = {}
    fig, ax = plt.subplots()
    for color, (name, kw) in zip(SERIES, variants, strict=True):
        se = np.array([mc_price(S, K, T, r, sigma, n_paths=int(n), seed=7, **kw).std_error for n in paths])
        ax.loglog(paths, se, "o-", color=color, ms=4, label=name)
        out[name] = se
    ax.set_xlabel("Simulated paths")
    ax.set_ylabel("Standard error of the price")
    ax.set_title("Monte Carlo error falls like 1/√N; variance reduction shifts the line down")
    ax.legend()
    ax.text(paths[-1], out["plain"][-1] * 1.25, "slope −½", color=INK_2, ha="right", fontsize=9)
    save(fig, "convergence_mc.png")

    big = mc_price(S, K, T, r, sigma, n_paths=1_000_000, seed=11)
    plain_se, cv_se = out["plain"][-1], out["antithetic + control variate"][-1]
    return {
        "mc_slope": round(loglog_slope(paths, out["plain"]), 3),
        "variance_reduction_factor": round(float((plain_se / cv_se) ** 2), 1),
        "mc_price_1m": round(big.price, 4),
        "mc_stderr_1m": round(big.std_error, 5),
        "bs_price": round(bs, 4),
    }


if __name__ == "__main__":
    results = {"params": {"S": S, "K": K, "T": T, "r": r, "sigma": sigma}}
    results.update(crr_study())
    results.update(mc_study())
    update_results("convergence", results)
