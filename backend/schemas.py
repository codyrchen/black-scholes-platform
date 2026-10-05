from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

OptionType = Literal["call", "put"]


class PriceRequest(BaseModel):
    spot: float = Field(gt=0)
    strike: float = Field(gt=0)
    maturity: float = Field(gt=0)
    rate: float
    volatility: float = Field(gt=0)
    dividend_yield: float = Field(default=0.0, ge=0)
    option_type: OptionType = "call"


class PriceResponse(BaseModel):
    price: float
    greeks: dict[str, float]
    response_time_ms: float


class ImpliedVolRequest(BaseModel):
    market_price: float = Field(gt=0)
    spot: float = Field(gt=0)
    strike: float = Field(gt=0)
    maturity: float = Field(gt=0)
    rate: float
    dividend_yield: float = Field(default=0.0, ge=0)
    option_type: OptionType = "call"


class PayoffRequest(BaseModel):
    strike: float = Field(gt=0)
    premium: float
    option_type: OptionType = "call"
    # Optional: include today's value curve alongside the expiry payoff.
    maturity: float | None = Field(default=None, gt=0)
    rate: float = 0.0
    volatility: float | None = Field(default=None, gt=0)
    dividend_yield: float = Field(default=0.0, ge=0)


class PayoffResponse(BaseModel):
    payoffs: list[dict[str, float]]


class DrillCheckRequest(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    response: float | int | str


class HedgeSimulateRequest(BaseModel):
    spot: float = Field(default=100.0, gt=0)
    strike: float = Field(default=100.0, gt=0)
    maturity: float = Field(default=0.25, gt=0, le=5)
    rate: float = Field(default=0.0, ge=-0.1, le=0.5)
    implied_vol: float = Field(default=0.2, gt=0, le=3)
    realized_vol: float | None = Field(default=None, gt=0, le=3)
    dividend_yield: float = Field(default=0.0, ge=0, le=0.5)
    option_type: OptionType = "call"
    steps: int = Field(default=20, ge=1, le=365)
    cost: float = Field(default=0.0, ge=0, le=0.05)
    seed: int | None = Field(default=None, ge=0, lt=2**31)


class HedgeStudyRequest(HedgeSimulateRequest):
    steps: list[int] = Field(default=[4, 13, 26, 52, 126, 252], min_length=1, max_length=8)
    paths: int = Field(default=2000, ge=100, le=5000)

    @field_validator("steps")
    @classmethod
    def _steps_in_range(cls, v: list[int]) -> list[int]:
        if any(not 1 <= s <= 365 for s in v):
            raise ValueError("each step count must be between 1 and 365")
        return v
