from __future__ import annotations

from pydantic import BaseModel, Field


class PriceRequest(BaseModel):
    spot: float = Field(gt=0)
    strike: float = Field(gt=0)
    maturity: float = Field(gt=0)
    rate: float
    volatility: float = Field(gt=0)
    option_type: str = Field(default="call", pattern="^(call|put)$")


class PriceResponse(BaseModel):
    price: float
    greeks: dict[str, float]
    response_time_ms: float


class PayoffRequest(BaseModel):
    strike: float = Field(gt=0)
    premium: float
    option_type: str = Field(default="call", pattern="^(call|put)$")


class PayoffResponse(BaseModel):
    payoffs: list[dict[str, float]]

