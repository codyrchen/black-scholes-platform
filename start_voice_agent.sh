#!/bin/bash
# Start the voice agent backend (Flask) and optional realtime WebSocket server.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
  echo "Copy .env.example to .env and add your OPENAI_API_KEY (and Twilio creds for phone calls)."
  cp -n .env.example .env 2>/dev/null || true
fi

echo "Starting Flask backend on port ${PORT:-5001}..."
python app.py &
FLASK_PID=$!

if [ "${VOICE_USE_REALTIME}" = "true" ]; then
  echo "Starting realtime media stream server on port ${VOICE_WS_PORT:-8765}..."
  python voice_stream_server.py &
  WS_PID=$!
  trap "kill $FLASK_PID $WS_PID 2>/dev/null" EXIT
else
  trap "kill $FLASK_PID 2>/dev/null" EXIT
fi

echo ""
echo "Voice agent API: http://localhost:${PORT:-5001}/api/v1/voice/status"
echo "Twilio webhook URL: \${PUBLIC_URL}/api/v1/voice/incoming"
echo "Press Ctrl+C to stop."
wait
