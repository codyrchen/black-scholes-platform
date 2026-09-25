# Black-Scholes Platform

A full-stack European option pricing platform with a Flask API and a React dashboard.

| Piece | Stack | What it does |
| --- | --- | --- |
| `backend/` | Flask + Pydantic + SpecTree | Black-Scholes pricing, Greeks, payoff curves, OpenAPI docs |
| `frontend/` | React 18 + Recharts | Pricing dashboard |

## Features

- Analytic Black-Scholes prices for European calls and puts (no SciPy dependency — the normal
  CDF is computed from `math.erf`).
- All five Greeks: delta, gamma, theta (per day), vega and rho (both per 1% move).
- Profit/loss payoff curves sampled over 100 spot points from 0.5×K to 1.5×K.
- Request validation via Pydantic, structured JSON error responses with a request ID, and
  JSON-formatted logs.
- Auto-generated OpenAPI docs at `/api/v1/docs`.

## Requirements

- Python 3.10+ (the code uses `X | None` syntax)
- Node.js 16+ and npm

## Quick start

```bash
git clone https://github.com/codyrchen/black-scholes-platform.git
cd black-scholes-platform

# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 app.py              # http://localhost:5001
```

In a second terminal:

```bash
cd frontend
npm install
npm start                   # http://localhost:3000
```

Both servers must run at the same time. The dashboard polls `/api/health` every five seconds
and shows a **Backend Status** badge, so you'll see immediately if the API isn't up.

Convenience scripts:

```bash
./start_backend.sh          # Flask only
python3 test_backend.py     # health-check the API
```

## Configuration

Everything has a working default; copy `.env.example` to `.env` to override.

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `5001` | Flask port. Port 5000 is avoided because macOS AirPlay claims it. |
| `HOST` | `0.0.0.0` | Flask bind address |
| `API_PREFIX` | `/api/v1` | Prefix for versioned routes and OpenAPI docs |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins for `/api/*` |
| `LOG_LEVEL` | `INFO` | Root log level |

The frontend reads `REACT_APP_API_URL` (default `http://localhost:5001`) — set it in
`frontend/.env` if the API runs elsewhere.

## API

Versioned routes live under `API_PREFIX` (default `/api/v1`). The unversioned `/api/price` and
`/api/payoff` paths are kept as aliases for the existing frontend and call the same handlers.

### `GET /api/health` · `GET /api/v1/health`

```json
{ "status": "ok", "message": "Backend is running" }
```

### `POST /api/v1/price`

```bash
curl -X POST http://localhost:5001/api/v1/price \
  -H 'Content-Type: application/json' \
  -d '{"spot":100,"strike":100,"maturity":0.25,"rate":0.05,"volatility":0.2,"option_type":"call"}'
```

`spot`, `strike`, `maturity` and `volatility` must be > 0; `rate` is a decimal (0.05 = 5%);
`option_type` is `call` or `put`.

```json
{
  "price": 4.6150,
  "greeks": { "delta": 0.5695, "gamma": 0.0393, "theta": -0.0287, "vega": 0.1964, "rho": 0.1308 },
  "response_time_ms": 0.21
}
```

Theta is quoted per calendar day; vega and rho per 1 percentage-point move.

### `POST /api/v1/payoff`

Takes `strike`, `premium` and `option_type`; returns 100 `{spot, payoff}` points spanning
0.5×K to 1.5×K.

### Errors

Failures return a consistent envelope and an `X-Request-Id` header:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request body.",
    "details": [ ... ],
    "request_id": "0d9e...5a"
  }
}
```

Codes in use: `VALIDATION_ERROR`, `INVALID_JSON`, `INTERNAL_SERVER_ERROR`.

## Project layout

```
app.py                     Flask entrypoint
test_backend.py            Health-check script
backend/
  __init__.py              create_app: CORS, OpenAPI, error handlers, blueprints
  config.py                Settings.from_env
  routes.py                /price, /payoff
  schemas.py               Pydantic request/response models
  pricing.py               Black-Scholes math and payoff curves
  errors.py                ApiError and JSON error handlers
  logging_config.py        JSON log formatter
frontend/src/
  App.js                   Pricing dashboard
```

## Deployment notes

`app.py` runs Flask's development server. For anything real, use the bundled gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5001 "backend:create_app()"
```

Note that **CORS defaults to `*`** — set `CORS_ORIGINS` to your actual frontend origin before
exposing this publicly.

## Troubleshooting

**Backend Status: ✗ Not Connected** — the Flask server isn't reachable. Check it's running, then
`python3 test_backend.py`. On macOS, port 5000 is taken by AirPlay Receiver, which is why the
default is 5001; if 5001 is also busy:

```bash
lsof -ti:5001 | xargs kill
```

**"Failed to fetch" in the browser** — usually CORS or a wrong API URL. Confirm
`REACT_APP_API_URL` matches where Flask is listening and that `CORS_ORIGINS` allows
`http://localhost:3000`.

See also [`QUICK_START.md`](QUICK_START.md) for a condensed two-terminal walkthrough.
