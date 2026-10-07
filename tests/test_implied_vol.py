import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from quant.black_scholes import greeks, price
from quant.implied_vol import ImpliedVolError, implied_vol


@settings(max_examples=300)
@given(
    st.floats(0.6, 1.6),
    st.floats(0.05, 3.0),
    st.floats(0.01, 3.0),
    st.floats(0.0, 0.1),
    st.sampled_from(["call", "put"]),
)
def test_round_trip(m, T, sigma, r, kind):
    S, K = 100.0, 100.0 * m
    target = price(S, K, T, r, sigma, kind=kind)
    vega = greeks(S, K, T, r, sigma, kind=kind)["vega"]
    # With almost no time value the price barely depends on sigma; skip those.
    assume(vega > 1e-4)
    iv, _ = implied_vol(target, S, K, T, r, kind=kind)
    # The solved vol always reprices the option...
    assert price(S, K, T, r, iv, kind=kind) == pytest.approx(target, abs=1e-9)
    # ...and recovers sigma tightly wherever vega makes sigma well determined.
    if vega > 1e-2:
        assert iv == pytest.approx(sigma, rel=1e-6)


def test_newton_converges_quickly_near_the_money():
    target = price(100, 100, 0.25, 0.05, 0.2)
    iv, iterations = implied_vol(target, 100, 100, 0.25, 0.05)
    assert iv == pytest.approx(0.2, abs=1e-8)
    assert 0 < iterations <= 5


def test_deep_otm_uses_fallback_and_is_accurate():
    target = price(100, 160, 0.25, 0.05, 0.35)
    iv, _ = implied_vol(target, 100, 160, 0.25, 0.05)
    assert iv == pytest.approx(0.35, rel=1e-6)


@pytest.mark.parametrize("bad_price", [0.0, 0.5, 110.0, 150.0])
def test_rejects_prices_outside_bounds(bad_price):
    # For this call the lower bound is S - K*exp(-rT), about 11.24; the upper bound is S = 110.
    with pytest.raises(ImpliedVolError):
        implied_vol(bad_price, 110, 100, 0.25, 0.05)
