from __future__ import annotations

import time

from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from spectree import Response

from backend.errors import ApiError
from backend.pricing import Inputs, greeks, payoff_curve, price
from backend.schemas import PayoffRequest, PayoffResponse, PriceRequest, PriceResponse

api_v1 = Blueprint("api_v1", __name__)


def _parse(model, data):
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise ApiError(
            status_code=400,
            code="VALIDATION_ERROR",
            message="Invalid request body.",
            details=e.errors(),
        )


@api_v1.post("/price")
def calculate_price_v1():
    start = time.time()
    if not request.is_json:
        raise ApiError(400, "INVALID_JSON", "Request must be JSON.")
    req = _parse(PriceRequest, request.get_json(silent=True) or {})
    inp = Inputs(
        spot=req.spot,
        strike=req.strike,
        maturity=req.maturity,
        rate=req.rate,
        volatility=req.volatility,
        option_type=req.option_type,
    )
    p = price(inp)
    g = greeks(inp)
    ms = (time.time() - start) * 1000.0
    resp = {"price": round(p, 4), "greeks": g, "response_time_ms": round(ms, 2)}
    return jsonify(resp)


@api_v1.post("/payoff")
def calculate_payoff_v1():
    if not request.is_json:
        raise ApiError(400, "INVALID_JSON", "Request must be JSON.")
    req = _parse(PayoffRequest, request.get_json(silent=True) or {})
    return jsonify({"payoffs": payoff_curve(req.strike, req.premium, req.option_type)})


# Backwards compatible legacy routes (previous frontend paths)
@api_v1.post("/legacy/price")
def calculate_price_legacy():
    return calculate_price_v1()


@api_v1.post("/legacy/payoff")
def calculate_payoff_legacy():
    return calculate_payoff_v1()

