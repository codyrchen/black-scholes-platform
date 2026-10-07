import pytest

from quant.binomial import crr_price
from quant.black_scholes import price
from quant.monte_carlo import mc_price

CASES = [
    (100, 100, 0.25, 0.05, 0.2, 0.0),
    (100, 110, 1.0, 0.03, 0.3, 0.02),
    (50, 45, 0.5, 0.0, 0.4, 0.0),
]


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("S,K,T,r,sigma,q", CASES)
def test_crr_european_converges_to_black_scholes(S, K, T, r, sigma, q, kind):
    bs = price(S, K, T, r, sigma, q, kind)
    assert crr_price(S, K, T, r, sigma, q, kind, steps=2000) == pytest.approx(bs, abs=5e-3)


def test_crr_error_shrinks_with_steps():
    bs = price(100, 100, 1.0, 0.05, 0.2)
    errors = [abs(crr_price(100, 100, 1.0, 0.05, 0.2, steps=n) - bs) for n in (50, 200, 800)]
    assert errors[0] > errors[1] > errors[2]


@pytest.mark.parametrize("S,K,T,r,sigma,q", CASES)
def test_american_put_at_least_european(S, K, T, r, sigma, q):
    euro = crr_price(S, K, T, r, sigma, q, "put", steps=500)
    amer = crr_price(S, K, T, r, sigma, q, "put", steps=500, american=True)
    assert amer >= euro - 1e-12


def test_american_put_has_early_exercise_premium():
    # Deep ITM put with high rates: early exercise is valuable.
    euro = crr_price(80, 100, 1.0, 0.08, 0.2, kind="put", steps=1000)
    amer = crr_price(80, 100, 1.0, 0.08, 0.2, kind="put", steps=1000, american=True)
    assert amer - euro > 0.5
    assert amer >= 20.0  # never below intrinsic


def test_american_call_without_dividends_equals_european():
    euro = crr_price(100, 95, 1.0, 0.05, 0.25, steps=800)
    amer = crr_price(100, 95, 1.0, 0.05, 0.25, steps=800, american=True)
    assert amer == pytest.approx(euro, abs=1e-10)


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("S,K,T,r,sigma,q", CASES)
def test_monte_carlo_within_four_standard_errors(S, K, T, r, sigma, q, kind):
    res = mc_price(S, K, T, r, sigma, q, kind, n_paths=200_000, seed=42)
    bs = price(S, K, T, r, sigma, q, kind)
    assert abs(res.price - bs) < 4 * res.std_error


def test_variance_reduction_reduces_standard_error():
    plain = mc_price(100, 100, 1.0, 0.05, 0.2, n_paths=100_000, seed=1, antithetic=False, control_variate=False)
    reduced = mc_price(100, 100, 1.0, 0.05, 0.2, n_paths=100_000, seed=1)
    assert reduced.std_error < 0.5 * plain.std_error


def test_crr_rejects_bad_probability():
    with pytest.raises(ValueError):
        crr_price(100, 100, 1.0, 0.5, 0.01, steps=2)
