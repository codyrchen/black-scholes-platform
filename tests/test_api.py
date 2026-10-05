import pytest

PRICE_BODY = {"spot": 100, "strike": 100, "maturity": 0.25, "rate": 0.05, "volatility": 0.2, "option_type": "call"}


def test_health(client):
    assert client.get("/api/health").json["status"] == "ok"


@pytest.mark.parametrize("path", ["/api/v1/price", "/api/price"])
def test_price(client, path):
    r = client.post(path, json=PRICE_BODY)
    assert r.status_code == 200
    assert r.json["price"] == pytest.approx(4.615, abs=1e-3)
    # Quoting units: theta per day, vega and rho per 1%.
    assert r.json["greeks"]["theta"] == pytest.approx(-0.0287, abs=1e-4)
    assert r.json["greeks"]["vega"] == pytest.approx(0.1964, abs=1e-4)


def test_price_with_dividend(client):
    plain = client.post("/api/v1/price", json=PRICE_BODY).json["price"]
    div = client.post("/api/v1/price", json={**PRICE_BODY, "dividend_yield": 0.03}).json["price"]
    assert div < plain


def test_price_validation_error(client):
    r = client.post("/api/v1/price", json={**PRICE_BODY, "spot": -5})
    assert r.status_code == 400
    assert r.json["error"]["code"] == "VALIDATION_ERROR"
    assert r.headers["X-Request-Id"]


def test_non_json_rejected(client):
    r = client.post("/api/v1/price", data="spot=100")
    assert r.status_code == 400 and r.json["error"]["code"] == "INVALID_JSON"


def test_implied_vol(client):
    body = {"market_price": 4.615, "spot": 100, "strike": 100, "maturity": 0.25, "rate": 0.05}
    r = client.post("/api/v1/implied-vol", json=body)
    assert r.status_code == 200
    assert r.json["implied_vol"] == pytest.approx(0.2, abs=1e-4)


def test_implied_vol_out_of_bounds(client):
    body = {"market_price": 150, "spot": 100, "strike": 100, "maturity": 0.25, "rate": 0.05}
    r = client.post("/api/v1/implied-vol", json=body)
    assert r.status_code == 422 and r.json["error"]["code"] == "NO_IMPLIED_VOL"


def test_payoff_with_value_curve(client):
    r = client.post("/api/v1/payoff", json={"strike": 100, "premium": 4.6, "maturity": 0.25, "volatility": 0.2})
    points = r.json["payoffs"]
    assert len(points) == 100
    assert all("value" in p for p in points)
    # Before expiry, a long option is worth at least its expiry payoff.
    assert all(p["value"] >= p["payoff"] - 1e-3 for p in points)


def test_drill_round_and_check(client):
    r = client.get("/api/v1/drills?count=5&seed=3&category=mental_math,greeks")
    assert r.status_code == 200
    questions = r.json["questions"]
    assert len(questions) == 5
    assert all("answer" not in q for q in questions)
    checked = client.post("/api/v1/drills/check", json={"id": questions[0]["id"], "response": 0}).json
    assert set(checked) >= {"correct", "answer", "answer_display", "explanation"}


def test_drill_bad_filters(client):
    assert client.get("/api/v1/drills?category=astrology").status_code == 400
    assert client.get("/api/v1/drills?count=500").status_code == 400
    assert client.post("/api/v1/drills/check", json={"id": "nope-1", "response": 1}).status_code == 404


def test_drill_categories(client):
    cats = client.get("/api/v1/drills/categories").json["categories"]
    assert {c["id"] for c in cats} == {"mental_math", "greeks", "pricing", "arbitrage"}


def test_hedging_simulate(client):
    r = client.post("/api/v1/hedging/simulate", json={"steps": 10, "seed": 5})
    assert r.status_code == 200
    body = r.json
    assert len(body["spots"]) == 11 and len(body["deltas"]) == 10
    assert body["bs_hedge_pnl"][0] == 0
    assert body["bs_hedge_pnl"][-1] == pytest.approx(body["breakdown"]["total"], abs=1e-3)


def test_hedging_study(client):
    r = client.post("/api/v1/hedging/study", json={"steps": [10, 160], "paths": 1000, "seed": 1})
    rows = r.json["results"]
    assert rows[0]["std"] > 2.5 * rows[1]["std"]


def test_hedging_validation(client):
    assert client.post("/api/v1/hedging/study", json={"steps": [0]}).status_code == 400
    assert client.post("/api/v1/hedging/simulate", json={"steps": 10_000}).status_code == 400
