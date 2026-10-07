"""Seeded options interview drills.

Every question is generated deterministically from ``(generator name, seed)``,
so the API can hand out questions without storing anything and re-create the
same question when the answer comes back. Every answer is computed with the
pricing library rather than hard-coded.

Question ids look like ``"put_call_parity-123456"``.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field

from quant.black_scholes import greeks, price
from quant.implied_vol import implied_vol

CATEGORIES = {
    "mental_math": "Mental math",
    "greeks": "Greeks intuition",
    "pricing": "Pricing",
    "arbitrage": "Arbitrage spotting",
}
DIFFICULTIES = ("easy", "medium", "hard")


@dataclass(frozen=True)
class Question:
    id: str
    category: str
    difficulty: str
    prompt: str
    answer: float  # numeric answer, or the index of the correct choice
    explanation: str
    choices: list[str] | None = None
    unit: str | None = None
    rel_tol: float = 0.0
    abs_tol: float = 0.0
    # The interview rule-of-thumb estimate, when there is one. Tests assert the
    # checker accepts it, so the tolerances are honest about the shortcut.
    shortcut: float | None = None
    extra: dict = field(default_factory=dict)

    @property
    def answer_type(self) -> str:
        return "choice" if self.choices is not None else "numeric"

    def is_correct(self, response) -> bool:
        if self.choices is not None:
            try:
                return int(response) == int(self.answer)
            except (TypeError, ValueError):
                return False
        try:
            value = float(response)
        except (TypeError, ValueError):
            return False
        if not math.isfinite(value):
            return False
        allowed = max(self.abs_tol, self.rel_tol * abs(self.answer))
        return abs(value - self.answer) <= allowed + 1e-12

    def answer_display(self) -> str:
        if self.choices is not None:
            return self.choices[int(self.answer)]
        return _fmt(self.answer, self.unit)

    def public(self) -> dict:
        """The question as shown before answering (no answer, no explanation)."""
        out = {
            "id": self.id,
            "category": self.category,
            "difficulty": self.difficulty,
            "prompt": self.prompt,
            "answer_type": self.answer_type,
            "unit": self.unit,
        }
        if self.choices is not None:
            out["choices"] = list(self.choices)
        else:
            out["tolerance"] = self.tolerance_text()
        return out

    def tolerance_text(self) -> str:
        if self.unit == "shares":
            return "exact"
        if self.rel_tol and self.abs_tol:
            return f"within {self.rel_tol:.0%} or {_fmt(self.abs_tol, self.unit)}"
        if self.rel_tol:
            return f"within {self.rel_tol:.1%}".replace(".0%", "%")
        return f"within {_fmt(self.abs_tol, self.unit)}"


def _fmt(x: float, unit: str | None) -> str:
    if unit == "$":
        return f"${x:,.2f}"
    if unit == "%":
        return f"{x:.2f}%"
    if unit == "shares":
        return f"{x:,.0f} shares"
    return f"{x:,.4g}"


def _pct(x: float) -> str:
    return f"{x * 100:g}%"


def _years(T: float) -> str:
    return "1 year" if T == 1 else f"{T:g} years"


_TENORS = [  # (label, years)
    ("1 week", 1 / 52),
    ("1 month", 1 / 12),
    ("3 months", 0.25),
    ("6 months", 0.5),
    ("1 year", 1.0),
]


# --------------------------------------------------------------------------
# Generators. Each takes a random.Random and returns Question kwargs.
# --------------------------------------------------------------------------

def _atm_call(rng: random.Random) -> dict:
    S = rng.choice([50, 80, 100, 120, 200, 250, 400])
    sigma = rng.choice([0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50])
    label, T = rng.choice(_TENORS[1:])
    exact = price(S, S, T, 0.0, sigma)
    approx = 0.4 * sigma * math.sqrt(T) * S
    return dict(
        prompt=(
            f"Estimate the price of an at-the-money call. Spot ${S}, implied vol "
            f"{_pct(sigma)}, expiry {label}, rates ≈ 0."
        ),
        answer=exact,
        unit="$",
        rel_tol=0.05,
        shortcut=approx,
        explanation=(
            f"ATM call ≈ 0.4 · σ · √T · S = 0.4 × {sigma:g} × {math.sqrt(T):.3f} × {S} = {approx:.2f}. "
            f"(0.4 ≈ 1/√(2π).) Exact Black-Scholes: {exact:.2f}."
        ),
    )


def _atm_straddle(rng: random.Random) -> dict:
    S = rng.choice([40, 100, 150, 200, 300, 500])
    sigma = rng.choice([0.15, 0.20, 0.25, 0.30, 0.35, 0.45, 0.60])
    label, T = rng.choice(_TENORS)
    exact = price(S, S, T, 0.0, sigma) + price(S, S, T, 0.0, sigma, kind="put")
    approx = 0.8 * sigma * math.sqrt(T) * S
    return dict(
        prompt=(
            f"Estimate the price of an at-the-money straddle (call + put). Spot ${S}, "
            f"implied vol {_pct(sigma)}, expiry {label}, rates ≈ 0."
        ),
        answer=exact,
        unit="$",
        rel_tol=0.05,
        shortcut=approx,
        explanation=(
            f"An ATM call and put are each ≈ 0.4·σ·√T·S, so the straddle ≈ 0.8·σ·√T·S = "
            f"0.8 × {sigma:g} × {math.sqrt(T):.3f} × {S} = {approx:.2f}. Exact: {exact:.2f}."
        ),
    )


def _implied_vol_from_straddle(rng: random.Random) -> dict:
    S = rng.choice([50, 100, 200, 400])
    sigma = rng.choice([0.12, 0.18, 0.22, 0.28, 0.35, 0.45, 0.55])
    label, T = rng.choice(_TENORS[1:])
    straddle = round(price(S, S, T, 0.0, sigma) + price(S, S, T, 0.0, sigma, kind="put"), 2)
    # The vol that reproduces the rounded straddle exactly (call = straddle / 2 at r = 0).
    exact, _ = implied_vol(straddle / 2.0, S, S, T, 0.0)
    approx = straddle / (0.8 * S * math.sqrt(T))
    return dict(
        prompt=(
            f"The at-the-money straddle on a ${S} stock expiring in {label} costs ${straddle:.2f}. "
            f"Roughly what implied vol is the market pricing? (Answer in %, rates ≈ 0.)"
        ),
        answer=exact * 100,
        unit="%",
        rel_tol=0.05,
        shortcut=approx * 100,
        explanation=(
            f"Invert straddle ≈ 0.8·σ·√T·S: σ ≈ {straddle:.2f} / (0.8 × {S} × {math.sqrt(T):.3f}) "
            f"= {approx:.1%}. Solving Black-Scholes exactly gives {exact:.2%}."
        ),
    )


def _daily_move(rng: random.Random) -> dict:
    S = rng.choice([20, 50, 100, 160, 250, 400, 800])
    sigma = rng.choice([0.16, 0.24, 0.32, 0.40, 0.48, 0.64, 0.80])
    exact = S * sigma / math.sqrt(252)
    approx = S * sigma / 16
    return dict(
        prompt=(
            f"A ${S} stock has implied vol {_pct(sigma)}. What one-standard-deviation daily move "
            f"(in dollars) does that imply? Assume 252 trading days a year."
        ),
        answer=exact,
        unit="$",
        rel_tol=0.03,
        shortcut=approx,
        explanation=(
            f"Daily vol = σ / √252 ≈ σ / 16 (the 'rule of 16'). {_pct(sigma)} / 16 = "
            f"{sigma / 16:.2%}, so the move ≈ ${approx:.2f}. Exactly: ${exact:.2f}."
        ),
    )


def _forward_price(rng: random.Random) -> dict:
    S = rng.choice([50, 80, 100, 125, 200, 400])
    r = rng.choice([0.02, 0.03, 0.04, 0.05, 0.06])
    q = rng.choice([0.0, 0.0, 0.01, 0.02, 0.03])
    label, T = rng.choice(_TENORS[2:])
    exact = S * math.exp((r - q) * T)
    approx = S * (1 + (r - q) * T)
    return dict(
        prompt=(
            f"Spot is ${S}, the risk-free rate is {_pct(r)} and the dividend yield is {_pct(q)} "
            f"(both continuously compounded). What is the {label} forward price?"
        ),
        answer=exact,
        unit="$",
        rel_tol=0.002,
        shortcut=approx,
        explanation=(
            f"F = S · e^((r − q)T) ≈ S · (1 + (r − q)T) = {S} × (1 + {r - q:.2f} × {T:g}) "
            f"= {approx:.2f}. Exactly: {exact:.3f}."
        ),
    )


def _put_call_parity(rng: random.Random) -> dict:
    S = rng.choice([90, 95, 100, 105, 110])
    K = 100
    r = rng.choice([0.0, 0.02, 0.04, 0.05])
    T = rng.choice([0.25, 0.5, 1.0])
    sigma = rng.choice([0.15, 0.2, 0.25, 0.3])
    C = round(price(S, K, T, r, sigma), 2)
    pv_k = K * math.exp(-r * T)
    P = C - S + pv_k
    return dict(
        prompt=(
            f"A European call (strike {K}, {_years(T)} to expiry) trades at ${C:.2f}. Spot is ${S}, "
            f"rates are {_pct(r)} continuously compounded, no dividends. What should the put with "
            f"the same strike and expiry cost?"
        ),
        answer=P,
        unit="$",
        abs_tol=0.05,
        explanation=(
            f"Put-call parity: C − P = S − K·e^(−rT). K·e^(−rT) = {pv_k:.2f}, so "
            f"P = C − S + K·e^(−rT) = {C:.2f} − {S} + {pv_k:.2f} = {P:.2f}."
        ),
    )


def _greek_sign(rng: random.Random) -> dict:
    side = rng.choice(["long", "short"])
    kind = rng.choice(["call", "put"])
    greek = rng.choice(["delta", "gamma", "vega", "theta"])
    value = greeks(100, 100, 0.25, 0.0, 0.2, kind=kind)[greek] * (1 if side == "long" else -1)
    answer = 0 if value > 0 else 1
    why = {
        "gamma": "Gamma and vega are positive for any long option (convexity in spot and vol)",
        "vega": "Gamma and vega are positive for any long option (convexity in spot and vol)",
        "theta": "Long options lose time value (theta < 0); the seller collects it",
        "delta": "Calls gain when spot rises (delta > 0); puts lose (delta < 0)",
    }[greek]
    return dict(
        prompt=f"Is the {greek} of a {side} {kind} position positive or negative?",
        choices=["Positive", "Negative"],
        answer=answer,
        explanation=f"{why}. Selling flips the sign, so a {side} {kind} has {greek} {value:+.4f} here.",
    )


_SCALING = [
    # (description, greek, factor applied, parameter changed)
    ("ATM gamma when time to expiry is quartered", "gamma", "T", 0.25),
    ("ATM vega when time to expiry is quartered", "vega", "T", 0.25),
    ("ATM theta when time to expiry is quartered", "theta", "T", 0.25),
    ("the ATM call price when time to expiry quadruples", "price", "T", 4.0),
    ("the ATM call price when implied vol doubles", "price", "sigma", 2.0),
    ("ATM gamma when implied vol doubles", "gamma", "sigma", 2.0),
]
_SCALING_CHOICES = ["×0.25", "×0.5", "×1", "×2", "×4"]
_SCALING_VALUES = [0.25, 0.5, 1.0, 2.0, 4.0]
_SCALING_WHY = {
    "gamma": "ATM gamma ≈ 0.4 / (S·σ·√T), so it scales like 1/(σ√T)",
    "vega": "ATM vega ≈ 0.4·S·√T, so it scales like √T",
    "theta": "ATM theta ≈ −0.2·S·σ/√T, so it scales like 1/√T",
    "price": "The ATM price ≈ 0.4·σ·√T·S, so it scales like σ√T",
}


def _greek_scaling(rng: random.Random) -> dict:
    desc, greek, param, factor = rng.choice(_SCALING)
    S = 100.0
    T = rng.choice([0.1, 0.25, 0.5])
    sigma = rng.choice([0.15, 0.2, 0.25])

    def value(T_, sigma_):
        if greek == "price":
            return price(S, S, T_, 0.0, sigma_)
        return greeks(S, S, T_, 0.0, sigma_)[greek]

    after = value(T * factor, sigma) if param == "T" else value(T, sigma * factor)
    ratio = after / value(T, sigma)
    answer = min(range(len(_SCALING_VALUES)), key=lambda i: abs(math.log(ratio / _SCALING_VALUES[i])))
    return dict(
        prompt=f"Roughly how does {desc} change?",
        choices=_SCALING_CHOICES,
        answer=answer,
        explanation=f"{_SCALING_WHY[greek]}. Computed ratio here: ×{ratio:.3f}.",
    )


def _largest_greek(rng: random.Random) -> dict:
    greek = rng.choice(["gamma", "vega", "theta"])
    S = 100
    T = rng.choice([0.1, 0.25, 0.5])
    sigma = rng.choice([0.2, 0.3])
    while True:
        strikes = sorted(rng.sample([70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130], 4))
        vals = [abs(greeks(S, K, T, 0.0, sigma)[greek]) for K in strikes]
        top = sorted(vals, reverse=True)
        if top[0] > 1.05 * top[1]:
            break
    answer = vals.index(top[0])
    word = {"gamma": "the most gamma", "vega": "the most vega", "theta": "the most time decay (theta)"}[greek]
    return dict(
        prompt=(
            f"Spot is ${S}, vol {_pct(sigma)}, {_years(T)} to expiry. Which call has {word}?"
        ),
        choices=[f"Strike {K}" for K in strikes],
        answer=answer,
        explanation=(
            f"Gamma, vega and theta all peak near the money, where the option is most uncertain to "
            f"finish in or out. |{greek}| by strike: "
            + ", ".join(f"{K}: {v:.4f}" for K, v in zip(strikes, vals, strict=True))
            + "."
        ),
    )


def _hedge_shares(rng: random.Random) -> dict:
    side = rng.choice(["buy", "sell"])
    kind = rng.choice(["call", "put"])
    contracts = rng.choice([2, 5, 10, 20, 25, 40, 50])
    abs_delta = rng.choice([0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9])
    delta = abs_delta if kind == "call" else -abs_delta
    position_delta = contracts * 100 * delta * (1 if side == "buy" else -1)
    shares = -position_delta
    return dict(
        prompt=(
            f"You {side} {contracts} {kind} contracts (100 shares each), each with delta "
            f"{delta:+.2f}. How many shares must you buy to be delta neutral? "
            f"(Enter a negative number to sell.)"
        ),
        answer=shares,
        unit="shares",
        abs_tol=0.5,
        explanation=(
            f"Position delta = {'+' if side == 'buy' else '−'}{contracts} × 100 × {delta:+.2f} = "
            f"{position_delta:+,.0f} shares, so trade {shares:+,.0f} shares to offset it."
        ),
    )


def _random_market(rng: random.Random):
    S = rng.choice([40, 75, 100, 120, 150, 250])
    K = round(S * rng.choice([0.8, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2]))
    T = rng.choice([0.25, 0.5, 0.75, 1.0])
    r = rng.choice([0.01, 0.03, 0.05])
    sigma = rng.choice([0.15, 0.2, 0.25, 0.3, 0.4])
    kind = rng.choice(["call", "put"])
    return S, K, T, r, sigma, kind


def _bs_price(rng: random.Random) -> dict:
    S, K, T, r, sigma, kind = _random_market(rng)
    p = price(S, K, T, r, sigma, kind=kind)
    return dict(
        prompt=(
            f"Price a European {kind} with Black-Scholes: S = {S}, K = {K}, T = {_years(T)}, "
            f"r = {_pct(r)}, σ = {_pct(sigma)}, no dividends. (A calculator is fine.)"
        ),
        answer=p,
        unit="$",
        rel_tol=0.01,
        abs_tol=0.01,
        explanation=_bs_explanation(S, K, T, r, sigma, kind) + f" Price = {p:.4f}.",
    )


def _bs_delta(rng: random.Random) -> dict:
    S, K, T, r, sigma, kind = _random_market(rng)
    d = greeks(S, K, T, r, sigma, kind=kind)["delta"]
    rule = "Call delta = N(d1)." if kind == "call" else "Put delta = N(d1) − 1."
    return dict(
        prompt=(
            f"What is the Black-Scholes delta of a European {kind}? S = {S}, K = {K}, "
            f"T = {_years(T)}, r = {_pct(r)}, σ = {_pct(sigma)}."
        ),
        answer=d,
        abs_tol=0.01,
        explanation=_bs_explanation(S, K, T, r, sigma, kind) + f" {rule} Delta = {d:.4f}.",
    )


def _bs_explanation(S, K, T, r, sigma, kind) -> str:
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return f"d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T) = {d1:.4f}, d2 = d1 − σ√T = {d2:.4f}."


def _implied_vol_q(rng: random.Random) -> dict:
    while True:
        S, K, T, r, sigma, kind = _random_market(rng)
        quote = round(price(S, K, T, r, sigma, kind=kind), 2)
        # Skip quotes where rounding to cents leaves little time value to invert.
        try:
            iv, _ = implied_vol(quote, S, K, T, r, kind=kind)
        except ValueError:
            continue
        if abs(iv - sigma) < 0.01:
            break
    return dict(
        prompt=(
            f"A European {kind} with S = {S}, K = {K}, T = {_years(T)}, r = {_pct(r)} trades at "
            f"${quote:.2f}. What is its implied volatility (in %)?"
        ),
        answer=iv * 100,
        unit="%",
        abs_tol=0.5,
        explanation=(
            f"Solve BS(σ) = {quote:.2f} for σ, e.g. with Newton's method: σ ← σ − (BS(σ) − price) / vega. "
            f"Implied vol = {iv:.2%}."
        ),
    )


_PARITY_CHOICES = [
    "No arbitrage",
    "Conversion: sell the call, buy the put, buy the stock",
    "Reversal: buy the call, sell the put, short the stock",
]


def _parity_arb(rng: random.Random) -> dict:
    S = rng.choice([48, 95, 100, 102, 110])
    K = 100 if S > 60 else 50
    r = rng.choice([0.02, 0.04, 0.05])
    T = rng.choice([0.25, 0.5, 1.0])
    sigma = rng.choice([0.2, 0.25, 0.3])
    pv_k = K * math.exp(-r * T)
    C = price(S, K, T, r, sigma)
    P = C - S + pv_k
    case = rng.randrange(3)
    error = rng.choice([0.6, 0.8, 1.0, 1.5, 2.0])
    if case == 1:
        C += error  # call rich relative to the put
    elif case == 2:
        P += error  # put rich relative to the call
    C, P = round(C, 2), round(P, 2)
    gap = C - P - (S - pv_k)
    answer = 0 if abs(gap) < 0.1 else (1 if gap > 0 else 2)
    return dict(
        prompt=(
            f"S = {S}, K = {K}, T = {_years(T)}, r = {_pct(r)} (continuous), no dividends. "
            f"The call trades at ${C:.2f} and the put at ${P:.2f}. Is there an arbitrage, "
            f"and which trade captures it?"
        ),
        choices=_PARITY_CHOICES,
        answer=answer,
        explanation=(
            f"Parity requires C − P = S − K·e^(−rT) = {S - pv_k:.2f}. Here C − P = {C - P:.2f}. "
            + (
                "They agree, so there is no arbitrage."
                if answer == 0
                else (
                    f"The call is {abs(gap):.2f} too rich relative to the put: sell C, buy P, "
                    f"buy S, and lock in K at expiry."
                    if answer == 1
                    else f"The put is {abs(gap):.2f} too rich relative to the call: buy C, sell P, "
                    f"short S, and pay K at expiry."
                )
            )
        ),
    )


def _butterfly_arb(rng: random.Random) -> dict:
    S = 100
    K2 = rng.choice([95, 100, 105])
    h = rng.choice([5, 10])
    K1, K3 = K2 - h, K2 + h
    T = rng.choice([0.25, 0.5])
    r = 0.0
    sigma = rng.choice([0.2, 0.3])
    C1, C2, C3 = (price(S, K, T, r, sigma) for K in (K1, K2, K3))
    case = rng.randrange(3)
    if case == 1:
        C2 = (C1 + C3) / 2 + rng.choice([0.3, 0.5, 1.0])  # middle too rich: fly costs < 0
    elif case == 2:
        C1 = 2 * C2 - C3 + h + rng.choice([0.3, 0.5, 1.0])  # wing too rich: fly costs > max payoff
    C1, C2, C3 = round(C1, 2), round(C2, 2), round(C3, 2)
    fly = C1 - 2 * C2 + C3
    answer = 1 if fly < 0 else (2 if fly > h else 0)
    return dict(
        prompt=(
            f"Calls on the same stock and expiry (rates ≈ 0): strike {K1} at ${C1:.2f}, "
            f"strike {K2} at ${C2:.2f}, strike {K3} at ${C3:.2f}. Is there an arbitrage?"
        ),
        choices=[
            "No arbitrage",
            f"Buy the butterfly (long {K1}, short 2× {K2}, long {K3})",
            f"Sell the butterfly (short {K1}, long 2× {K2}, short {K3})",
        ],
        answer=answer,
        explanation=(
            f"A butterfly pays between 0 and {h} at expiry, so its price must lie in [0, {h}]. "
            f"Here it costs C1 − 2·C2 + C3 = {fly:.2f}. "
            + (
                "That's inside the range, so prices are consistent (convex in strike)."
                if answer == 0
                else (
                    "That's negative: you are paid to buy something that never pays less than 0."
                    if answer == 1
                    else f"That's more than the maximum payoff of {h}: sell it."
                )
            )
        ),
    )


def _vertical_arb(rng: random.Random) -> dict:
    S = 100
    K1 = rng.choice([90, 95, 100])
    K2 = K1 + rng.choice([5, 10])
    T = rng.choice([0.25, 0.5])
    r = 0.0
    sigma = rng.choice([0.2, 0.3])
    C1, C2 = price(S, K1, T, r, sigma), price(S, K2, T, r, sigma)
    case = rng.randrange(3)
    if case == 1:
        C1 = C2 - rng.choice([0.2, 0.5, 1.0])  # lower strike cheaper: buy the spread for a credit
    elif case == 2:
        C1 = C2 + (K2 - K1) + rng.choice([0.2, 0.5, 1.0])  # spread worth more than its max payoff
    C1, C2 = round(C1, 2), round(C2, 2)
    spread = C1 - C2
    answer = 1 if spread < 0 else (2 if spread > K2 - K1 else 0)
    return dict(
        prompt=(
            f"Calls on the same stock and expiry (rates ≈ 0): strike {K1} at ${C1:.2f}, "
            f"strike {K2} at ${C2:.2f}. Is there an arbitrage?"
        ),
        choices=[
            "No arbitrage",
            f"Buy the {K1} call, sell the {K2} call",
            f"Sell the {K1} call, buy the {K2} call",
        ],
        answer=answer,
        explanation=(
            f"A {K1}/{K2} call spread pays between 0 and {K2 - K1}, so it must cost between 0 and "
            f"{K2 - K1}. It costs C({K1}) − C({K2}) = {spread:.2f}. "
            + (
                "That's within bounds."
                if answer == 0
                else (
                    "Negative: buy the spread and get paid for a payoff that is never negative."
                    if answer == 1
                    else "More than the maximum payoff: sell the spread."
                )
            )
        ),
    )


@dataclass(frozen=True)
class Generator:
    name: str
    category: str
    difficulty: str
    fn: Callable[[random.Random], dict]


GENERATORS: dict[str, Generator] = {
    g.name: g
    for g in [
        Generator("atm_call", "mental_math", "easy", _atm_call),
        Generator("atm_straddle", "mental_math", "easy", _atm_straddle),
        Generator("daily_move", "mental_math", "easy", _daily_move),
        Generator("forward_price", "mental_math", "medium", _forward_price),
        Generator("put_call_parity", "mental_math", "medium", _put_call_parity),
        Generator("implied_vol_from_straddle", "mental_math", "hard", _implied_vol_from_straddle),
        Generator("greek_sign", "greeks", "easy", _greek_sign),
        Generator("hedge_shares", "greeks", "easy", _hedge_shares),
        Generator("greek_scaling", "greeks", "medium", _greek_scaling),
        Generator("largest_greek", "greeks", "medium", _largest_greek),
        Generator("bs_delta", "pricing", "medium", _bs_delta),
        Generator("bs_price", "pricing", "hard", _bs_price),
        Generator("implied_vol", "pricing", "hard", _implied_vol_q),
        Generator("parity_arb", "arbitrage", "medium", _parity_arb),
        Generator("vertical_arb", "arbitrage", "medium", _vertical_arb),
        Generator("butterfly_arb", "arbitrage", "hard", _butterfly_arb),
    ]
}

_MAX_SEED = 2**31


def make_question(name: str, seed: int) -> Question:
    gen = GENERATORS[name]
    kwargs = gen.fn(random.Random(f"{name}:{seed}"))
    return Question(id=f"{name}-{seed}", category=gen.category, difficulty=gen.difficulty, **kwargs)


def question_from_id(question_id: str) -> Question:
    """Re-create a question from its id. Raises KeyError/ValueError for unknown ids."""
    name, _, seed = question_id.rpartition("-")
    if name not in GENERATORS:
        raise KeyError(question_id)
    seed_int = int(seed)
    if not 0 <= seed_int < _MAX_SEED:
        raise ValueError(question_id)
    return make_question(name, seed_int)


def generate_round(
    count: int = 10,
    seed: int | None = None,
    categories: list[str] | None = None,
    difficulties: list[str] | None = None,
) -> list[Question]:
    """A round of ``count`` questions, mixing generators that match the filters."""
    pool = [
        g.name
        for g in GENERATORS.values()
        if (not categories or g.category in categories)
        and (not difficulties or g.difficulty in difficulties)
    ]
    if not pool:
        raise ValueError("no drills match those filters")
    rng = random.Random(seed)
    out: list[Question] = []
    last = None
    for _ in range(count):
        # Avoid the same generator twice in a row when there is a choice.
        options = [n for n in pool if n != last] or pool
        name = rng.choice(options)
        out.append(make_question(name, rng.randrange(_MAX_SEED)))
        last = name
    return out
