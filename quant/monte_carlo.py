"""Monte Carlo pricing of European options under geometric Brownian motion."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from quant.black_scholes import OptionKind


@dataclass(frozen=True)
class MCResult:
    price: float
    std_error: float
    n_paths: int


def mc_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    kind: OptionKind = "call",
    n_paths: int = 100_000,
    seed: int | None = None,
    antithetic: bool = True,
    control_variate: bool = True,
) -> MCResult:
    """Estimate the option price by sampling the terminal spot exactly.

    Variance reduction:

    - antithetic: each normal draw z is paired with -z, and the pair's average
      payoff is one sample (so ``n_paths`` draws give ``n_paths / 2`` samples).
    - control variate: the discounted terminal spot, whose expectation is
      known exactly (S * exp(-q T)), with the regression-optimal coefficient.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    rng = np.random.default_rng(seed)
    n_draws = n_paths // 2 if antithetic else n_paths
    z = rng.standard_normal(n_draws)

    drift = (r - q - 0.5 * sigma * sigma) * T
    vol = sigma * np.sqrt(T)
    disc = np.exp(-r * T)
    sign = 1.0 if kind == "call" else -1.0

    def discounted(zs):
        s_T = S * np.exp(drift + vol * zs)
        return disc * np.maximum(sign * (s_T - K), 0.0), disc * s_T

    payoff, control = discounted(z)
    if antithetic:
        payoff_b, control_b = discounted(-z)
        payoff = 0.5 * (payoff + payoff_b)
        control = 0.5 * (control + control_b)

    if control_variate:
        expected_control = S * np.exp(-q * T)
        cov = np.cov(payoff, control)
        beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else 0.0
        payoff = payoff - beta * (control - expected_control)

    n = payoff.size
    return MCResult(
        price=float(payoff.mean()),
        std_error=float(payoff.std(ddof=1) / np.sqrt(n)),
        n_paths=n_paths,
    )
