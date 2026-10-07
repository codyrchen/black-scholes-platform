from __future__ import annotations

import secrets
import time

import numpy as np
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from backend.errors import ApiError
from backend.pricing import payoff_curve, quoted_greeks
from backend.schemas import (
    DrillCheckRequest,
    HedgeSimulateRequest,
    HedgeStudyRequest,
    ImpliedVolRequest,
    PayoffRequest,
    PriceRequest,
)
from quant import drills
from quant.black_scholes import price
from quant.hedging import hedge_mtm, simulate_hedge
from quant.implied_vol import ImpliedVolError, implied_vol

api_v1 = Blueprint("api_v1", __name__)


def _parse(model, data):
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise ApiError(
            status_code=400,
            code="VALIDATION_ERROR",
            message="Invalid request body.",
            details=e.errors(include_url=False, include_context=False),
        ) from None


def _json_body(model):
    if not request.is_json:
        raise ApiError(400, "INVALID_JSON", "Request must be JSON.")
    return _parse(model, request.get_json(silent=True) or {})


def _r(x: float, digits: int = 6) -> float:
    # + 0.0 turns -0.0 into 0.0 so the JSON doesn't show "-0.0".
    return round(float(x), digits) + 0.0


def _rlist(xs, digits: int = 4) -> list[float]:
    return [_r(x, digits) for x in np.asarray(xs).ravel()]


@api_v1.post("/price")
def calculate_price_v1():
    start = time.perf_counter()
    req = _json_body(PriceRequest)
    args = (req.spot, req.strike, req.maturity, req.rate, req.volatility, req.dividend_yield, req.option_type)
    p = price(*args)
    g = quoted_greeks(*args)
    ms = (time.perf_counter() - start) * 1000.0
    return jsonify(
        {
            "price": _r(p, 4),
            "greeks": {k: _r(v, 6) for k, v in g.items()},
            "response_time_ms": round(ms, 2),
        }
    )


@api_v1.post("/implied-vol")
def calculate_implied_vol_v1():
    req = _json_body(ImpliedVolRequest)
    try:
        sigma, iterations = implied_vol(
            req.market_price, req.spot, req.strike, req.maturity, req.rate,
            req.dividend_yield, req.option_type,
        )
    except ImpliedVolError as e:
        raise ApiError(422, "NO_IMPLIED_VOL", str(e)) from None
    return jsonify(
        {
            "implied_vol": _r(sigma, 6),
            "method": "newton" if iterations > 0 else "brent",
            "iterations": max(iterations, 0),
        }
    )


@api_v1.post("/payoff")
def calculate_payoff_v1():
    req = _json_body(PayoffRequest)
    return jsonify(
        {
            "payoffs": payoff_curve(
                req.strike, req.premium, req.option_type,
                maturity=req.maturity, rate=req.rate,
                volatility=req.volatility, dividend_yield=req.dividend_yield,
            )
        }
    )


# --------------------------------------------------------------------------
# Drills
# --------------------------------------------------------------------------

def _csv_arg(name: str, allowed) -> list[str] | None:
    raw = request.args.get(name, "").strip()
    if not raw:
        return None
    values = [v.strip() for v in raw.split(",") if v.strip()]
    bad = [v for v in values if v not in allowed]
    if bad:
        raise ApiError(400, "VALIDATION_ERROR", f"Unknown {name}: {', '.join(bad)}",
                       details={"allowed": list(allowed)})
    return values


@api_v1.get("/drills/categories")
def drill_categories():
    return jsonify(
        {
            "categories": [
                {
                    "id": cid,
                    "name": label,
                    "difficulties": sorted(
                        {g.difficulty for g in drills.GENERATORS.values() if g.category == cid},
                        key=drills.DIFFICULTIES.index,
                    ),
                }
                for cid, label in drills.CATEGORIES.items()
            ],
            "difficulties": list(drills.DIFFICULTIES),
        }
    )


@api_v1.get("/drills")
def drill_round():
    categories = _csv_arg("category", drills.CATEGORIES)
    difficulties = _csv_arg("difficulty", drills.DIFFICULTIES)
    try:
        count = int(request.args.get("count", 10))
        seed_arg = request.args.get("seed")
        seed = int(seed_arg) if seed_arg is not None else secrets.randbelow(2**31)
    except ValueError:
        raise ApiError(400, "VALIDATION_ERROR", "count and seed must be integers.") from None
    if not 1 <= count <= 50:
        raise ApiError(400, "VALIDATION_ERROR", "count must be between 1 and 50.")
    try:
        questions = drills.generate_round(count, seed, categories, difficulties)
    except ValueError as e:
        raise ApiError(400, "VALIDATION_ERROR", str(e)) from None
    return jsonify({"seed": seed, "questions": [q.public() for q in questions]})


@api_v1.post("/drills/check")
def drill_check():
    req = _json_body(DrillCheckRequest)
    try:
        q = drills.question_from_id(req.id)
    except (KeyError, ValueError):
        raise ApiError(404, "UNKNOWN_QUESTION", f"No drill question with id {req.id!r}.") from None
    return jsonify(
        {
            "id": q.id,
            "correct": q.is_correct(req.response),
            "answer": _r(q.answer, 6),
            "answer_display": q.answer_display(),
            "explanation": q.explanation,
        }
    )


# --------------------------------------------------------------------------
# Delta hedging
# --------------------------------------------------------------------------

@api_v1.post("/hedging/simulate")
def hedging_simulate():
    """One simulated path with the Black-Scholes delta hedger and the unhedged book."""
    req = _json_body(HedgeSimulateRequest)
    seed = req.seed if req.seed is not None else secrets.randbelow(2**31)
    h = simulate_hedge(
        req.spot, req.strike, req.maturity, req.rate, req.implied_vol, req.realized_vol,
        req.dividend_yield, req.option_type, req.steps, n_paths=1, cost=req.cost, seed=seed,
    )
    no_hedge = hedge_mtm(
        h.spots, np.zeros_like(h.deltas), h.option_values, h.premium,
        req.maturity, req.rate, req.dividend_yield, req.cost,
    )
    bs_hedge = hedge_mtm(
        h.spots, h.deltas, h.option_values, h.premium,
        req.maturity, req.rate, req.dividend_yield, req.cost,
    )
    return jsonify(
        {
            "seed": seed,
            "premium": _r(h.premium, 4),
            "times": _rlist(h.times, 6),
            "spots": _rlist(h.spots[0]),
            "option_values": _rlist(h.option_values[0]),
            "deltas": _rlist(h.deltas[0]),
            "bs_hedge_pnl": _rlist(bs_hedge[0]),
            "no_hedge_pnl": _rlist(no_hedge[0]),
            "breakdown": {
                "total": _r(h.pnl[0], 4),
                "gamma": _r(h.gamma_pnl[0], 4),
                "theta": _r(h.theta_pnl[0], 4),
                "residual": _r(h.residual_pnl[0], 4),
            },
        }
    )


@api_v1.post("/hedging/study")
def hedging_study():
    """Distribution of final hedged P&L for several rebalancing frequencies."""
    req = _json_body(HedgeStudyRequest)
    seed = req.seed if req.seed is not None else secrets.randbelow(2**31)
    rows = []
    for steps in req.steps:
        h = simulate_hedge(
            req.spot, req.strike, req.maturity, req.rate, req.implied_vol, req.realized_vol,
            req.dividend_yield, req.option_type, steps, n_paths=req.paths, cost=req.cost, seed=seed,
        )
        rows.append(
            {
                "steps": steps,
                "mean": _r(h.pnl.mean(), 4),
                "std": _r(h.pnl.std(ddof=1), 4),
                "p05": _r(np.percentile(h.pnl, 5), 4),
                "p95": _r(np.percentile(h.pnl, 95), 4),
            }
        )
    return jsonify({"seed": seed, "premium": _r(h.premium, 4), "results": rows})
