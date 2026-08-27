"""Standalone WebSocket server for Twilio Media Streams + OpenAI Realtime."""

from __future__ import annotations

import asyncio
import os

from voice_agent.media_bridge import run_media_server


def main() -> None:
    host = os.getenv("VOICE_WS_HOST", "0.0.0.0")
    port = int(os.getenv("VOICE_WS_PORT", "8765"))
    asyncio.run(run_media_server(host, port))


if __name__ == "__main__":
    main()
