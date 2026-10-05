"""API-facing helpers built on the ``quant`` library."""

from __future__ import annotations

import numpy as np

from quant.black_scholes import greeks as bs_greeks
from quant.black_scholes import price as bs_price


def quoted_greeks(S, K, T, r, sigma, q, kind) -> dict[str, float]:
    """Greeks in trader quoting units: theta per calendar day, vega and rho per 1% move."""
    g = bs_greeks(S, K, T, r, sigma, q, kind)
    return {
        "delta": g["delta"],
        "gamma": g["gamma"],
        "theta": g["theta"] / 365.0,
        "vega": g["vega"] / 100.0,
        "rho": g["rho"] / 100.0,
    }


def payoff_curve(
    strike: float,
    premium: float,
    option_type: str,
    points: int = 100,
    maturity: float | None = None,
    rate: float = 0.0,
    volatility: float | None = None,
    dividend_yield: float = 0.0,
) -> list[dict[str, float]]:
    """P&L of a long option over spot from 0.5K to 1.5K.

    ``payoff`` is the P&L at expiry. When ``maturity`` and ``volatility`` are
    given, ``value`` is the P&L today (Black-Scholes value minus premium).
    """
    spots = np.linspace(0.5 * strike, 1.5 * strike, points)
    sign = 1.0 if option_type == "call" else -1.0
    payoffs = np.maximum(sign * (spots - strike), 0.0) - premium
    values = None
    if maturity is not None and volatility is not None:
        values = bs_price(spots, strike, maturity, rate, volatility, dividend_yield, option_type) - premium

    out = []
    for i, s in enumerate(spots):
        point = {"spot": round(float(s), 2), "payoff": round(float(payoffs[i]), 4)}
        if values is not None:
            point["value"] = round(float(values[i]), 4)
        out.append(point)
    return out
