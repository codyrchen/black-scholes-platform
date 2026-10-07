"""Implied volatility: invert Black-Scholes-Merton for sigma."""

from __future__ import annotations

import math

from scipy.optimize import brentq

from quant.black_scholes import OptionKind, greeks, price, price_bounds

VOL_LOWER = 1e-6
VOL_UPPER = 10.0


class ImpliedVolError(ValueError):
    """The price cannot be produced by any volatility (it violates no-arbitrage bounds)."""


def initial_guess(target: float, S: float, T: float) -> float:
    # Brenner-Subrahmanyam: an ATM call is worth about 0.4 * S * sigma * sqrt(T),
    # i.e. sigma ~ sqrt(2*pi / T) * C / S. Clamped so Newton starts somewhere sane.
    guess = math.sqrt(2.0 * math.pi / T) * target / S
    return min(max(guess, 0.05), 3.0)


def implied_vol(
    target: float,
    S: float,
    K: float,
    T: float,
    r: float,
    q: float = 0.0,
    kind: OptionKind = "call",
    tol: float = 1e-10,
    max_newton: int = 20,
) -> tuple[float, int]:
    """Return ``(sigma, newton_iterations)`` such that ``price(sigma) == target``.

    Newton's method on vega converges quadratically near the money. Far from the
    money vega is tiny and Newton can overshoot, so any step that leaves the
    bracket or stalls falls back to Brent's method, which always converges.
    ``newton_iterations`` is -1 when the Brent fallback produced the result.
    """
    if T <= 0:
        raise ImpliedVolError("maturity must be positive")
    lower, upper = price_bounds(S, K, T, r, q, kind)
    # A price at (or numerically at) a bound corresponds to sigma = 0 or infinity.
    eps = 1e-12 * max(1.0, upper)
    if not (lower + eps < target < upper - eps):
        raise ImpliedVolError(
            f"price {target:.6g} is outside the no-arbitrage range ({lower:.6g}, {upper:.6g})"
        )

    sigma = initial_guess(target, S, T)
    for i in range(1, max_newton + 1):
        diff = price(S, K, T, r, sigma, q, kind) - target
        if abs(diff) < tol:
            return sigma, i
        vega = greeks(S, K, T, r, sigma, q, kind)["vega"]
        if vega < 1e-8:
            break
        step = diff / vega
        sigma -= step
        if not (VOL_LOWER < sigma < VOL_UPPER):
            break
        if abs(step) < 1e-14:
            return sigma, i

    def f(s: float) -> float:
        return price(S, K, T, r, s, q, kind) - target

    sigma = brentq(f, VOL_LOWER, VOL_UPPER, xtol=1e-14, rtol=1e-14, maxiter=500)
    return sigma, -1
