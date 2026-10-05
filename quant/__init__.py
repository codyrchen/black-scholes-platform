"""Option pricing library behind the platform: Black-Scholes, implied vol,
binomial trees, Monte Carlo and delta-hedging simulation."""

from quant.binomial import crr_price
from quant.black_scholes import greeks, price, price_bounds
from quant.hedging import simulate_hedge
from quant.implied_vol import ImpliedVolError, implied_vol
from quant.monte_carlo import mc_price

__all__ = [
    "ImpliedVolError",
    "crr_price",
    "greeks",
    "implied_vol",
    "mc_price",
    "price",
    "price_bounds",
    "simulate_hedge",
]
