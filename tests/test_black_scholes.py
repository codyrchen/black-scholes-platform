import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from quant.black_scholes import greeks, price, price_bounds


# Hull, Options, Futures and Other Derivatives, Example 15.6:
# S=42, K=40, T=0.5, r=10%, sigma=20% -> call 4.76, put 0.81.
def test_hull_reference_values():
    assert price(42, 40, 0.5, 0.10, 0.20) == pytest.approx(4.7594, abs=1e-4)
    assert price(42, 40, 0.5, 0.10, 0.20, kind="put") == pytest.approx(0.8086, abs=1e-4)


def test_atm_reference_value():
    # Widely quoted value for S=K=100, T=1, r=5%, sigma=20%.
    assert price(100, 100, 1.0, 0.05, 0.20) == pytest.approx(10.4506, abs=1e-4)


spots = st.floats(1.0, 500.0)
moneyness = st.floats(0.5, 2.0)
maturities = st.floats(0.01, 5.0)
rates = st.floats(-0.02, 0.15)
vols = st.floats(0.02, 1.5)
yields = st.floats(0.0, 0.1)


@settings(max_examples=300)
@given(spots, moneyness, maturities, rates, vols, yields)
def test_put_call_parity(S, m, T, r, sigma, q):
    K = S * m
    c = price(S, K, T, r, sigma, q)
    p = price(S, K, T, r, sigma, q, kind="put")
    assert c - p == pytest.approx(S * math.exp(-q * T) - K * math.exp(-r * T), abs=1e-9 * S)


@settings(max_examples=300)
@given(spots, moneyness, maturities, rates, vols, yields, st.sampled_from(["call", "put"]))
def test_price_within_no_arbitrage_bounds(S, m, T, r, sigma, q, kind):
    K = S * m
    lower, upper = price_bounds(S, K, T, r, q, kind)
    v = price(S, K, T, r, sigma, q, kind)
    assert lower - 1e-9 * S <= v <= upper + 1e-9 * S


@settings(max_examples=200)
@given(spots, moneyness, maturities, rates, vols, yields, st.sampled_from(["call", "put"]))
def test_price_increases_with_vol(S, m, T, r, sigma, q, kind):
    K = S * m
    assert price(S, K, T, r, sigma * 1.1, q, kind) >= price(S, K, T, r, sigma, q, kind) - 1e-12


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize(
    "S,K,T,r,sigma,q",
    [
        (100, 100, 0.25, 0.05, 0.2, 0.0),
        (100, 120, 1.0, 0.03, 0.35, 0.02),
        (50, 40, 0.1, 0.0, 0.5, 0.0),
        (250, 260, 2.0, 0.08, 0.15, 0.04),
    ],
)
def test_greeks_match_finite_differences(S, K, T, r, sigma, q, kind):
    g = greeks(S, K, T, r, sigma, q, kind)

    def f(**bump):
        args = dict(S=S, K=K, T=T, r=r, sigma=sigma, q=q)
        args.update(bump)
        return price(args["S"], K, args["T"], args["r"], args["sigma"], q, kind)

    h = 1e-5 * S
    assert g["delta"] == pytest.approx((f(S=S + h) - f(S=S - h)) / (2 * h), abs=1e-7)
    # A larger step for the second difference, to keep cancellation error down.
    h = 1e-3 * S
    assert g["gamma"] == pytest.approx((f(S=S + h) - 2 * f() + f(S=S - h)) / h**2, rel=1e-4)
    assert g["vega"] == pytest.approx((f(sigma=sigma + 1e-5) - f(sigma=sigma - 1e-5)) / 2e-5, rel=1e-6)
    assert g["rho"] == pytest.approx((f(r=r + 1e-6) - f(r=r - 1e-6)) / 2e-6, rel=1e-5, abs=1e-6)
    # theta = dV/dt = -dV/dT
    assert g["theta"] == pytest.approx(-(f(T=T + 1e-6) - f(T=T - 1e-6)) / 2e-6, rel=1e-5, abs=1e-6)


def test_vectorized_matches_scalar():
    S = np.linspace(50, 150, 11)
    vec = price(S, 100, 0.5, 0.03, 0.25, 0.01, "put")
    assert vec.shape == S.shape
    for s, v in zip(S, vec, strict=True):
        assert v == pytest.approx(price(float(s), 100, 0.5, 0.03, 0.25, 0.01, "put"), abs=1e-12)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_expiry_and_zero_vol_limits(kind):
    # At expiry: intrinsic value.
    assert price(110, 100, 0.0, 0.05, 0.2, kind=kind) == pytest.approx(10.0 if kind == "call" else 0.0)
    # Zero vol: discounted forward intrinsic, and the price is continuous as vol -> 0.
    v0 = price(110, 100, 1.0, 0.05, 0.0, kind=kind)
    assert v0 == pytest.approx(price(110, 100, 1.0, 0.05, 1e-6, kind=kind), abs=1e-9)
    g = greeks(110, 100, 0.0, 0.05, 0.2, kind=kind)
    assert g["gamma"] == 0.0 and g["vega"] == 0.0
    assert g["delta"] == (1.0 if kind == "call" else 0.0)


def test_deep_otm_greeks_not_rounded_away():
    g = greeks(100, 200, 0.1, 0.0, 0.2)
    assert 0 < g["gamma"] < 1e-10
    assert 0 < g["vega"]


def test_invalid_kind():
    with pytest.raises(ValueError):
        price(100, 100, 1, 0, 0.2, kind="straddle")
