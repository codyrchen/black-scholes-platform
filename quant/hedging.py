"""Discrete delta hedging of a short European option under GBM.

The trader sells one option at the Black-Scholes price (using the *implied*
vol), then holds ``delta`` shares, rebalancing ``n_steps`` times. The stock
actually moves with the *realized* vol. With continuous rebalancing and
realized == implied vol, the hedged P&L would be exactly zero; this module
shows what happens in between.

Per step, the hedged P&L of the short option is approximately

    0.5 * Gamma * S^2 * (sigma_implied^2 * dt - (dS / S)^2)

i.e. the option seller collects "theta" (the first term) and pays out
"gamma" on every realized move (the second). The breakdown returned by
:func:`simulate_hedge` reports these two sums and the residual (discretization
error and transaction costs).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from quant.black_scholes import OptionKind, greeks, intrinsic, price


def gbm_paths(S0, T, mu, sigma, n_steps, n_paths, rng):
    """Exact GBM sampling. Returns an array of shape (n_paths, n_steps + 1)."""
    dt = T / n_steps
    z = rng.standard_normal((n_paths, n_steps))
    log_inc = (mu - 0.5 * sigma * sigma) * dt + sigma * np.sqrt(dt) * z
    log_paths = np.concatenate([np.zeros((n_paths, 1)), np.cumsum(log_inc, axis=1)], axis=1)
    return S0 * np.exp(log_paths)


@dataclass(frozen=True)
class HedgeResult:
    times: np.ndarray          # (n_steps + 1,)
    spots: np.ndarray          # (n_paths, n_steps + 1)
    option_values: np.ndarray  # (n_paths, n_steps + 1), BS value at implied vol
    deltas: np.ndarray         # (n_paths, n_steps), hedge held over each step
    pnl: np.ndarray            # (n_paths,), final hedged P&L of the short option
    gamma_pnl: np.ndarray      # (n_paths,)
    theta_pnl: np.ndarray      # (n_paths,)
    residual_pnl: np.ndarray   # (n_paths,)
    premium: float


def hedge_mtm(spots, hedges, option_values, premium, T, r, q=0.0, cost=0.0):
    """Mark-to-market P&L of a short option hedged with arbitrary share holdings.

    ``spots`` and ``option_values`` have shape (..., n_steps + 1) and ``hedges``
    shape (..., n_steps): ``hedges[..., i]`` shares are held from step i to
    step i + 1. Cash earns r, the stock pays a continuous yield q, and every
    trade costs ``cost * |shares traded| * spot``. The last column is the final
    P&L after unwinding the hedge at expiry (``option_values[..., -1]`` should be
    the payoff).
    """
    spots = np.asarray(spots, dtype=float)
    hedges = np.asarray(hedges, dtype=float)
    option_values = np.asarray(option_values, dtype=float)
    n_steps = hedges.shape[-1]
    dt = T / n_steps
    growth = np.exp(r * dt)
    div = np.exp(q * dt) - 1.0

    mtm = np.empty(spots.shape)
    held = np.zeros(spots.shape[:-1])
    cash = np.full(spots.shape[:-1], float(premium))
    for i in range(n_steps):
        mtm[..., i] = cash + held * spots[..., i] - option_values[..., i]
        trade = hedges[..., i] - held
        cash = cash - trade * spots[..., i] - cost * np.abs(trade) * spots[..., i]
        held = hedges[..., i]
        cash = cash * growth + held * spots[..., i] * div
    s_T = spots[..., -1]
    mtm[..., -1] = cash + held * s_T - cost * np.abs(held) * s_T - option_values[..., -1]
    return mtm


def hedge_pnl(spots, hedges, premium, K, T, r, q=0.0, kind: OptionKind = "call", cost=0.0):
    """Final P&L of a short option hedged with ``hedges`` (see :func:`hedge_mtm`)."""
    spots = np.asarray(spots, dtype=float)
    values = np.zeros(spots.shape)
    values[..., -1] = intrinsic(spots[..., -1], K, kind)
    return hedge_mtm(spots, hedges, values, premium, T, r, q, cost)[..., -1]


def simulate_hedge(
    S0: float,
    K: float,
    T: float,
    r: float,
    sigma_implied: float,
    sigma_realized: float | None = None,
    q: float = 0.0,
    kind: OptionKind = "call",
    n_steps: int = 52,
    n_paths: int = 1,
    cost: float = 0.0,
    seed: int | None = None,
) -> HedgeResult:
    """Simulate selling one option and delta hedging it ``n_steps`` times."""
    sigma_realized = sigma_implied if sigma_realized is None else sigma_realized
    rng = np.random.default_rng(seed)
    times = np.linspace(0.0, T, n_steps + 1)
    tau = T - times  # time to expiry at each step
    dt = T / n_steps

    # Real-world drift does not matter for the hedge; use the risk-neutral one.
    spots = gbm_paths(S0, T, r - q, sigma_realized, n_steps, n_paths, rng)

    option_values = price(spots, K, tau, r, sigma_implied, q, kind)
    g = greeks(spots[:, :-1], K, tau[:-1], r, sigma_implied, q, kind)
    deltas, gammas = g["delta"], g["gamma"]
    premium = float(option_values[0, 0])

    pnl = hedge_mtm(spots, deltas, option_values, premium, T, r, q, cost)[:, -1]

    s = spots[:, :-1]
    ds = np.diff(spots, axis=1)
    gamma_pnl = (-0.5 * gammas * ds * ds).sum(axis=1)
    theta_pnl = (0.5 * gammas * s * s * sigma_implied ** 2 * dt).sum(axis=1)

    return HedgeResult(
        times=times,
        spots=spots,
        option_values=option_values,
        deltas=deltas,
        pnl=pnl,
        gamma_pnl=gamma_pnl,
        theta_pnl=theta_pnl,
        residual_pnl=pnl - gamma_pnl - theta_pnl,
        premium=premium,
    )
