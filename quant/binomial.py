"""Cox-Ross-Rubinstein binomial tree for European and American options."""

from __future__ import annotations

import numpy as np

from quant.black_scholes import OptionKind


def crr_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    kind: OptionKind = "call",
    steps: int = 500,
    american: bool = False,
) -> float:
    """Price an option on a CRR tree with ``steps`` time steps.

    The European price converges to Black-Scholes at rate O(1/steps), with the
    error oscillating between odd and even step counts as the strike moves
    relative to the terminal nodes.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    if steps < 1:
        raise ValueError("steps must be >= 1")

    dt = T / steps
    u = np.exp(sigma * np.sqrt(dt))
    d = 1.0 / u
    growth = np.exp((r - q) * dt)
    p = (growth - d) / (u - d)
    if not 0.0 < p < 1.0:
        raise ValueError(
            f"risk-neutral probability {p:.4f} is outside (0, 1); increase steps or check inputs"
        )
    disc = np.exp(-r * dt)
    sign = 1.0 if kind == "call" else -1.0

    # Terminal spots, highest first: S * u^(steps - 2j) for j = 0..steps.
    j = np.arange(steps + 1)
    spots = S * u ** (steps - 2 * j)
    values = np.maximum(sign * (spots - K), 0.0)

    for _ in range(steps):
        values = disc * (p * values[:-1] + (1.0 - p) * values[1:])
        if american:
            spots = spots[:-1] * d  # spots one step earlier: S * u^(n - 2j)
            values = np.maximum(values, sign * (spots - K))

    return float(values[0])
