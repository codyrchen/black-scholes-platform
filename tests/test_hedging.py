import numpy as np
import pytest

from quant.hedging import hedge_pnl, simulate_hedge

BASE = dict(S0=100, K=100, T=0.25, r=0.05, sigma_implied=0.2, n_paths=4000, seed=0)


def test_hedge_error_shrinks_like_one_over_sqrt_n():
    coarse = simulate_hedge(**BASE, n_steps=25).pnl.std()
    fine = simulate_hedge(**BASE, n_steps=400).pnl.std()
    # 16x more rebalancing -> about 4x smaller error.
    assert 3.0 < coarse / fine < 5.5


def test_hedged_pnl_is_unbiased_when_vols_match():
    h = simulate_hedge(**BASE, n_steps=100)
    assert abs(h.pnl.mean()) < 4 * h.pnl.std() / np.sqrt(h.pnl.size)


def test_short_option_loses_when_realized_vol_exceeds_implied():
    h = simulate_hedge(**BASE, sigma_realized=0.3, n_steps=100)
    assert h.pnl.mean() < -1.0
    h = simulate_hedge(**BASE, sigma_realized=0.1, n_steps=100)
    assert h.pnl.mean() > 1.0


def test_breakdown_sums_to_total_and_residual_is_small():
    h = simulate_hedge(**BASE, n_steps=200)
    np.testing.assert_allclose(h.gamma_pnl + h.theta_pnl + h.residual_pnl, h.pnl)
    assert h.residual_pnl.std() < 0.25 * h.pnl.std()


def test_transaction_costs_reduce_pnl():
    free = simulate_hedge(**BASE, n_steps=50)
    costly = simulate_hedge(**BASE, n_steps=50, cost=0.001)
    assert costly.pnl.mean() < free.pnl.mean()


def test_unhedged_short_call_pnl_is_premium_grown_minus_payoff():
    h = simulate_hedge(**{**BASE, "n_paths": 10}, n_steps=10)
    zero = np.zeros_like(h.deltas)
    pnl = hedge_pnl(h.spots, zero, h.premium, 100, 0.25, 0.05)
    expected = h.premium * np.exp(0.05 * 0.25) - np.maximum(h.spots[:, -1] - 100, 0)
    np.testing.assert_allclose(pnl, expected)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_put_hedging_works_too(kind):
    h = simulate_hedge(**BASE, n_steps=100, kind=kind)
    assert h.pnl.std() < 0.2 * h.premium
