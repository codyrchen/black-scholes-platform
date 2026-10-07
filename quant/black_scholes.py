"""Black-Scholes-Merton pricing and Greeks for European options.

All functions accept floats or numpy arrays (broadcast together) and return
values in "natural" units:

- theta is per year (divide by 365 for per-calendar-day),
- vega and rho are per 1.00 change in vol / rate (divide by 100 for per 1%).

The continuous dividend yield ``q`` defaults to 0, which recovers plain
Black-Scholes. When ``sigma * sqrt(T)`` is zero (expiry or zero vol) the
option is worth its discounted forward intrinsic value and the Greeks take
their limiting values.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from scipy.special import ndtr

OptionKind = Literal["call", "put"]

# Below this total volatility the option is treated as deterministic.
_MIN_TOTAL_VOL = 1e-12


def norm_pdf(x):
    return np.exp(-0.5 * np.square(x)) / np.sqrt(2.0 * np.pi)


def norm_cdf(x):
    # scipy's ndtr stays accurate deep in the tails, where 0.5 * (1 + erf)
    # loses precision to cancellation.
    return ndtr(x)


def _check_kind(kind: str) -> bool:
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    return kind == "call"


def _as_float(x):
    """Return a Python float for 0-d results so scalar callers get scalars."""
    x = np.asarray(x, dtype=float)
    return float(x) if x.ndim == 0 else x


def d1_d2(S, K, T, r, sigma, q=0.0):
    S, K, T, r, sigma, q = (np.asarray(a, dtype=float) for a in (S, K, T, r, sigma, q))
    total_vol = sigma * np.sqrt(np.maximum(T, 0.0))
    safe = np.where(total_vol > _MIN_TOTAL_VOL, total_vol, 1.0)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / safe
    d2 = d1 - total_vol
    return d1, d2, total_vol


def price(S, K, T, r, sigma, q=0.0, kind: OptionKind = "call"):
    """Black-Scholes-Merton price of a European call or put."""
    is_call = _check_kind(kind)
    d1, d2, total_vol = d1_d2(S, K, T, r, sigma, q)
    S, K, T, r, q = (np.asarray(a, dtype=float) for a in (S, K, T, r, q))
    disc_S = S * np.exp(-q * T)
    disc_K = K * np.exp(-r * T)

    if is_call:
        smooth = disc_S * norm_cdf(d1) - disc_K * norm_cdf(d2)
        intrinsic = np.maximum(disc_S - disc_K, 0.0)
    else:
        smooth = disc_K * norm_cdf(-d2) - disc_S * norm_cdf(-d1)
        intrinsic = np.maximum(disc_K - disc_S, 0.0)

    return _as_float(np.where(total_vol > _MIN_TOTAL_VOL, smooth, intrinsic))


def greeks(S, K, T, r, sigma, q=0.0, kind: OptionKind = "call") -> dict:
    """Delta, gamma, theta (per year), vega and rho (per unit) as a dict."""
    is_call = _check_kind(kind)
    d1, d2, total_vol = d1_d2(S, K, T, r, sigma, q)
    S, K, T, r, sigma, q = (np.asarray(a, dtype=float) for a in (S, K, T, r, sigma, q))
    live = total_vol > _MIN_TOTAL_VOL
    safe_total_vol = np.where(live, total_vol, 1.0)
    sqrt_T = np.sqrt(np.maximum(T, 0.0))
    safe_sqrt_T = np.where(sqrt_T > 0, sqrt_T, 1.0)

    df_q = np.exp(-q * T)
    df_r = np.exp(-r * T)
    pdf_d1 = norm_pdf(d1)

    gamma = np.where(live, df_q * pdf_d1 / (S * safe_total_vol), 0.0)
    vega = np.where(live, S * df_q * pdf_d1 * sqrt_T, 0.0)
    decay = -S * df_q * pdf_d1 * sigma / (2.0 * safe_sqrt_T)

    # Deterministic limit: exercise indicator on the discounted forward.
    itm_call = (S * df_q > K * df_r).astype(float)

    if is_call:
        n_d1 = np.where(live, norm_cdf(d1), itm_call)
        n_d2 = np.where(live, norm_cdf(d2), itm_call)
        delta = df_q * n_d1
        theta = np.where(live, decay, 0.0) - r * K * df_r * n_d2 + q * S * df_q * n_d1
        rho = K * T * df_r * n_d2
    else:
        n_md1 = np.where(live, norm_cdf(-d1), 1.0 - itm_call)
        n_md2 = np.where(live, norm_cdf(-d2), 1.0 - itm_call)
        delta = -df_q * n_md1
        theta = np.where(live, decay, 0.0) + r * K * df_r * n_md2 - q * S * df_q * n_md1
        rho = -K * T * df_r * n_md2

    return {
        "delta": _as_float(delta),
        "gamma": _as_float(gamma),
        "theta": _as_float(theta),
        "vega": _as_float(vega),
        "rho": _as_float(rho),
    }


def price_bounds(S, K, T, r, q=0.0, kind: OptionKind = "call") -> tuple[float, float]:
    """Model-free no-arbitrage (lower, upper) bounds for a European option."""
    is_call = _check_kind(kind)
    disc_S = S * np.exp(-q * T)
    disc_K = K * np.exp(-r * T)
    if is_call:
        return _as_float(np.maximum(disc_S - disc_K, 0.0)), _as_float(disc_S)
    return _as_float(np.maximum(disc_K - disc_S, 0.0)), _as_float(disc_K)


def intrinsic(S, K, kind: OptionKind = "call"):
    is_call = _check_kind(kind)
    S = np.asarray(S, dtype=float)
    return _as_float(np.maximum(S - K, 0.0) if is_call else np.maximum(K - S, 0.0))
