"""Implied-volatility smiles from listed option quotes.

The market's rate and dividend assumptions are backed out of put-call parity
instead of being guessed: for each expiry,

    C(K) - P(K) = DF * (F - K)

is linear in the strike, so a regression of (C - P) on K near the money gives
the discount factor DF = -slope and the forward F = intercept / DF. Implied
vols are then computed from out-of-the-money options only (puts below the
forward, calls above), which are the liquid ones.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from quant.implied_vol import ImpliedVolError, implied_vol


@dataclass(frozen=True)
class Quote:
    strike: float
    kind: str  # "call" | "put"
    bid: float
    ask: float

    @property
    def mid(self) -> float:
        return 0.5 * (self.bid + self.ask)


@dataclass(frozen=True)
class SmilePoint:
    strike: float
    log_moneyness: float  # ln(K / F)
    implied_vol: float
    kind: str


@dataclass(frozen=True)
class Smile:
    T: float
    forward: float
    discount_factor: float
    points: list[SmilePoint]

    @property
    def rate(self) -> float:
        return -math.log(self.discount_factor) / self.T

    def vol_at(self, k: float) -> float:
        """Implied vol at log-moneyness k, linearly interpolated."""
        ks = np.array([p.log_moneyness for p in self.points])
        vs = np.array([p.implied_vol for p in self.points])
        order = np.argsort(ks)
        return float(np.interp(k, ks[order], vs[order]))


def clean_quotes(quotes: list[Quote], max_rel_spread: float = 0.25) -> list[Quote]:
    """Drop quotes with no bid, crossed markets, or very wide spreads."""
    out = []
    for q in quotes:
        if q.bid <= 0 or q.ask <= q.bid:
            continue
        if (q.ask - q.bid) / q.mid > max_rel_spread:
            continue
        out.append(q)
    return out


def implied_forward(quotes: list[Quote], spot: float, n_strikes: int = 10) -> tuple[float, float]:
    """(forward, discount factor) from put-call parity on the strikes nearest spot."""
    calls = {q.strike: q.mid for q in quotes if q.kind == "call"}
    puts = {q.strike: q.mid for q in quotes if q.kind == "put"}
    both = sorted(set(calls) & set(puts), key=lambda k: abs(k - spot))[:n_strikes]
    if len(both) < 3:
        raise ValueError("need at least 3 strikes with both a call and a put quote")
    K = np.array(both)
    diff = np.array([calls[k] - puts[k] for k in both])
    slope, intercept = np.polyfit(K, diff, 1)
    df = -slope
    if not 0.5 < df <= 1.05:
        raise ValueError(f"implausible discount factor {df:.4f} from parity regression")
    return float(intercept / df), float(df)


def build_smile(quotes: list[Quote], spot: float, T: float) -> Smile:
    """Clean the quotes, back out F and DF from parity, and solve OTM implied vols."""
    quotes = clean_quotes(quotes)
    F, df = implied_forward(quotes, spot)
    r = -math.log(df) / T
    s_eff = F * df  # spot-equivalent with q = 0, so S_eff * exp(rT) = F
    points = []
    for q in sorted(quotes, key=lambda q: q.strike):
        otm = (q.kind == "put" and q.strike < F) or (q.kind == "call" and q.strike >= F)
        if not otm:
            continue
        try:
            sigma, _ = implied_vol(q.mid, s_eff, q.strike, T, r, 0.0, q.kind)
        except ImpliedVolError:
            continue
        points.append(SmilePoint(q.strike, math.log(q.strike / F), sigma, q.kind))
    return Smile(T=T, forward=F, discount_factor=df, points=points)
