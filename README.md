# Black-Scholes Platform

A full-stack European option pricing platform with a Flask API, a React dashboard, and an
optional AI voice agent that can answer customer service calls over the phone.

| Piece | Stack | What it does |
| --- | --- | --- |
| `backend/` | Flask + Pydantic + SpecTree | Black-Scholes pricing, Greeks, payoff curves, OpenAPI docs |
| `frontend/` | React 18 + Recharts | Pricing dashboard and browser-based voice agent demo |
| `voice_agent/` | OpenAI + Twilio | Tool-calling customer service agent for phone and text |

## Features

**Option pricing**
- Analytic Black-Scholes prices for European calls and puts (no SciPy dependency — the normal
  CDF is computed from `math.erf`).
- All five Greeks: delta, gamma, theta (per day), vega and rho (both per 1% move).
- Profit/loss payoff curves sampled over 100 spot points from 0.5×K to 1.5×K.
- Request validation via Pydantic, structured JSON error responses with a request ID, and
  JSON-formatted logs.
- Auto-generated OpenAPI docs at `/api/v1/docs`.

**AI voice agent**
- OpenAI chat model with function calling over a small customer-service knowledge base
  (orders, customer accounts, FAQ topics, ticket creation, human escalation).
- Twilio webhooks for real phone calls, using speech `<Gather>` turn-taking by default.
- Optional low-latency mode that bridges Twilio Media Streams to the OpenAI Realtime API
  over a standalone WebSocket server.
- Text chat + TTS endpoints so the agent can be exercised from the browser without a phone.

## Requirements

- Python 3.10+ (the code uses `X | None` syntax)
- Node.js 16+ and npm
- An OpenAI API key — only needed for the voice agent; option pricing works without one
- A Twilio account and phone number — only needed for real phone calls

## Quick start

```bash
git clone https://github.com/codyrchen/black-scholes-platform.git
cd black-scholes-platform

# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in keys if you want the voice agent
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
./start_voice_agent.sh      # creates .venv, installs deps, starts Flask (+ WS server if enabled)
python3 test_backend.py     # health-check the API
```

## Configuration

Copy `.env.example` to `.env`. Everything has a working default except the API credentials.

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `5001` | Flask port. Port 5000 is avoided because macOS AirPlay claims it. |
| `HOST` | `0.0.0.0` | Flask bind address |
| `API_PREFIX` | `/api/v1` | Prefix for versioned routes and OpenAPI docs |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins for `/api/*` |
| `LOG_LEVEL` | `INFO` | Root log level |
| `OPENAI_API_KEY` | — | Required for the voice agent, TTS, and realtime mode |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model for the agent |
| `OPENAI_TTS_VOICE` | `nova` | Voice used by `/api/v1/voice/tts` |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_PHONE_NUMBER` | — | Required for phone calls |
| `COMPANY_NAME` | `Black-Scholes Platform` | Used in the agent's system prompt and greeting |
| `AGENT_NAME` | `Alex` | Agent's name in the greeting |
| `PUBLIC_URL` | `http://localhost:5001` | Public base URL Twilio uses to reach webhooks (ngrok in dev) |
| `HUMAN_TRANSFER_NUMBER` | — | Number to `<Dial>` on escalation; without it the call ends after a ticket is promised |
| `VOICE_USE_REALTIME` | `false` | Switch from `<Gather>` turn-taking to Media Streams + Realtime |
| `VOICE_WS_PUBLIC_URL` | `ws://localhost:8765` | Public `wss://` URL of the media bridge |
| `VOICE_WS_PORT` / `VOICE_WS_HOST` | `8765` / `0.0.0.0` | Where `voice_stream_server.py` listens |
| `OPENAI_REALTIME_MODEL` | `gpt-4o-realtime-preview-2024-12-17` | Realtime model for the media bridge |

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

### Voice endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/voice/status` | Whether OpenAI/Twilio are configured, branding, greeting, sample order IDs |
| `POST` | `/api/v1/voice/chat` | Text conversation with the agent (`message`, optional `session_id`) |
| `POST` | `/api/v1/voice/chat/reset` | Drop a session and issue a fresh `session_id` |
| `POST` | `/api/v1/voice/tts` | `{"text": "..."}` → `audio/mpeg` |
| `POST` | `/api/v1/voice/incoming` | Twilio webhook — answers the call |
| `POST` | `/api/v1/voice/handle-speech` | Twilio webhook — one caller turn |
| `POST` | `/api/v1/voice/call-status` | Twilio status callback; cleans up finished sessions |

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

Codes in use: `VALIDATION_ERROR`, `INVALID_JSON`, `OPENAI_NOT_CONFIGURED`, `INTERNAL_SERVER_ERROR`.

## Setting up phone calls

1. Set `OPENAI_API_KEY` and the three `TWILIO_*` variables in `.env`.
2. Expose the backend publicly and point `PUBLIC_URL` at it:
   ```bash
   ngrok http 5001
   ```
3. In the Twilio console, on your number's Voice configuration:
   - **A call comes in** → webhook `POST {PUBLIC_URL}/api/v1/voice/incoming`
   - **Call status changes** → webhook `POST {PUBLIC_URL}/api/v1/voice/call-status`
4. Call the number. Conversation state is keyed by a `session_id` passed through the
   `handle-speech` webhook URL.

### Realtime (low-latency) mode

Default mode uses Twilio speech recognition with `<Gather>`: simple, but each turn round-trips
through transcription and TTS. For streaming audio instead:

```bash
export VOICE_USE_REALTIME=true
export VOICE_WS_PUBLIC_URL=wss://your-ngrok-ws-url.ngrok.io
python3 voice_stream_server.py        # or ./start_voice_agent.sh, which starts both
```

`voice_agent/media_bridge.py` transcodes between Twilio's 8 kHz mulaw and the Realtime API's
pcm16 and relays events in both directions. Note that this path needs a second public tunnel
for the WebSocket port, and that server-side VAD replaces `<Gather>` for turn detection.

## Agent tools and sample data

`voice_agent/knowledge.py` holds in-memory fixtures — swap it for a CRM or database in
production. The agent can call:

| Tool | Behaviour |
| --- | --- |
| `lookup_order` | Looks up `ORD-1001`, `ORD-1002`, `ORD-1003` |
| `lookup_customer` | Looks up `jane@example.com`, `john@example.com` |
| `get_faq` | Topics: `hours`, `refund`, `billing`, `api`, `cancel` |
| `create_support_ticket` | Mints a `TKT-XXXXXXXX` ticket in memory |
| `escalate_to_human` | Flags the session; the call is dialed to `HUMAN_TRANSFER_NUMBER` |

The agent loops through at most `MAX_TOOL_ROUNDS` (5) tool calls per turn before escalating.

## Project layout

```
app.py                     Flask entrypoint
voice_stream_server.py     Standalone WebSocket server for Realtime mode
test_backend.py            Health-check script
backend/
  __init__.py              create_app: CORS, OpenAPI, error handlers, blueprints
  config.py                Settings.from_env
  routes.py                /price, /payoff
  schemas.py               Pydantic request/response models
  pricing.py               Black-Scholes math and payoff curves
  voice_routes.py          Voice HTTP + Twilio webhook routes
  errors.py                ApiError and JSON error handlers
  logging_config.py        JSON log formatter
voice_agent/
  agent.py                 ConversationAgent (chat + tool loop + TTS)
  config.py                VoiceSettings.from_env
  prompts.py               System prompt
  tools.py                 Tool schemas and dispatch
  knowledge.py             Sample orders, customers, FAQ, tickets
  sessions.py              Thread-safe in-memory session store (1h TTL)
  twilio_handlers.py       TwiML for incoming/speech/status
  media_bridge.py          Twilio Media Streams ↔ OpenAI Realtime bridge
frontend/src/
  App.js                   Pricing dashboard
  VoiceAgent.js            Browser chat/voice demo
```

## Deployment notes

`app.py` runs Flask's development server. For anything real, use the bundled gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5001 "backend:create_app()"
```

Before exposing this publicly, be aware of what it does not yet do:

- **Twilio webhooks are unauthenticated.** Validate the `X-Twilio-Signature` header on
  `/incoming`, `/handle-speech` and `/call-status` — anyone who finds the URLs can drive the agent.
- **Sessions are in-process.** The store in `voice_agent/sessions.py` is a dict behind a lock, so
  multiple gunicorn workers won't share call state. Use Redis or sticky routing if you scale out.
- **CORS defaults to `*`.** Set `CORS_ORIGINS` to your actual frontend origin.
- **Tickets and knowledge are fixtures.** Nothing is persisted across restarts.
- Realtime mode needs a public `wss://` endpoint separate from the HTTP tunnel.

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

**`OPENAI_NOT_CONFIGURED` (503)** — `OPENAI_API_KEY` isn't set in the environment the Flask
process actually sees. `.env` is loaded by `app.py` at import time, so restart after editing it.

**Twilio calls connect but the agent never answers** — `PUBLIC_URL` must be the externally
reachable base URL; the `handle-speech` action URL is built from it, so a stale ngrok URL leaves
Twilio unable to complete the turn.

See also [`QUICK_START.md`](QUICK_START.md) for a condensed two-terminal walkthrough.
