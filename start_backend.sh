#!/bin/bash

# Start Flask backend server
echo "========================================="
echo "Starting Black-Scholes Backend Server"
echo "========================================="
echo ""
PORT="${PORT:-5001}"
echo "Server will run on: http://localhost:${PORT}"
echo "Press Ctrl+C to stop the server"
echo ""
echo "========================================="
echo ""

cd "$(dirname "$0")"
PORT="${PORT}" python3 app.py
