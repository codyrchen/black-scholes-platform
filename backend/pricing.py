from __future__ import annotations

import math
from dataclasses import dataclass


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    # Standard normal CDF via error function (no SciPy dependency).
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass(frozen=True)
class Inputs:
    spot: float
    strike: float
    maturity: float
    rate: float
    volatility: float
    option_type: str  # "call" | "put"


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def price(inp: Inputs) -> float:
    d1, d2 = _d1_d2(inp.spot, inp.strike, inp.maturity, inp.rate, inp.volatility)
    S, K, T, r = inp.spot, inp.strike, inp.maturity, inp.rate

    if inp.option_type == "call":
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def greeks(inp: Inputs) -> dict[str, float]:
    d1, d2 = _d1_d2(inp.spot, inp.strike, inp.maturity, inp.rate, inp.volatility)
    S, K, T, r, sigma = inp.spot, inp.strike, inp.maturity, inp.rate, inp.volatility

    if inp.option_type == "call":
        delta = _norm_cdf(d1)
    else:
        delta = _norm_cdf(d1) - 1.0

    gamma = _norm_pdf(d1) / (S * sigma * math.sqrt(T))

    if inp.option_type == "call":
        theta = (-S * _norm_pdf(d1) * sigma / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * _norm_cdf(d2)) / 365.0
        rho = K * T * math.exp(-r * T) * _norm_cdf(d2) / 100.0
    else:
        theta = (-S * _norm_pdf(d1) * sigma / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * _norm_cdf(-d2)) / 365.0
        rho = -K * T * math.exp(-r * T) * _norm_cdf(-d2) / 100.0

    vega = S * _norm_pdf(d1) * math.sqrt(T) / 100.0

    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 4),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "rho": round(rho, 4),
    }


def payoff_curve(strike: float, premium: float, option_type: str, points: int = 100) -> list[dict[str, float]]:
    # Mimic previous behavior: spot from 0.5K..1.5K
    start = strike * 0.5
    end = strike * 1.5
    step = (end - start) / (points - 1)
    out: list[dict[str, float]] = []
    for i in range(points):
        S = start + step * i
        if option_type == "call":
            payoff = max(S - strike, 0.0) - premium
        else:
            payoff = max(strike - S, 0.0) - premium
        out.append({"spot": round(S, 2), "payoff": round(payoff, 2)})
    return out

