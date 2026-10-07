import math

import pytest

from quant.black_scholes import price
from quant.smile import Quote, build_smile, clean_quotes


def true_vol(k: float) -> float:
    # A typical equity skew: higher vol for low strikes, a little curvature.
    return 0.18 - 0.25 * k + 0.6 * k * k


def synthetic_chain(S=450.0, T=0.25, r=0.045, q=0.015, half_spread=0.01):
    F = S * math.exp((r - q) * T)
    quotes = []
    for K in range(360, 541, 5):
        sigma = true_vol(math.log(K / F))
        for kind in ("call", "put"):
            mid = price(S, K, T, r, sigma, q, kind)
            quotes.append(Quote(K, kind, mid * (1 - half_spread), mid * (1 + half_spread)))
    return quotes, F, math.exp(-r * T)


def test_recovers_forward_discount_and_smile():
    quotes, F, df = synthetic_chain()
    smile = build_smile(quotes, spot=450.0, T=0.25)
    assert smile.forward == pytest.approx(F, rel=1e-3)
    assert smile.discount_factor == pytest.approx(df, abs=2e-3)
    assert len(smile.points) > 20
    for p in smile.points:
        assert p.implied_vol == pytest.approx(true_vol(p.log_moneyness), abs=0.004)
    # Only out-of-the-money options are used.
    assert all((p.kind == "put") == (p.strike < smile.forward) for p in smile.points)


def test_cleaning_drops_bad_quotes():
    good = Quote(100, "call", 1.0, 1.1)
    bad = [Quote(100, "put", 0.0, 0.2), Quote(105, "call", 2.0, 1.9), Quote(110, "call", 0.1, 0.5)]
    assert clean_quotes([good, *bad]) == [good]


def test_rejects_chain_without_parity_pairs():
    with pytest.raises(ValueError):
        build_smile([Quote(100, "call", 1.0, 1.1)], spot=100.0, T=0.25)
