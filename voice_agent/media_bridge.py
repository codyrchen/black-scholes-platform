from __future__ import annotations

"""
WebSocket bridge between Twilio Media Streams and OpenAI Realtime API.

Run alongside the Flask app when VOICE_USE_REALTIME=true.
Twilio sends mulaw 8kHz audio; OpenAI Realtime expects pcm16.
"""

import asyncio
import audioop
import base64
import json
import logging
import os
from typing import Any

import websockets

from voice_agent.config import VoiceSettings
from voice_agent.prompts import system_prompt

logger = logging.getLogger(__name__)

REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2024-12-17")
REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={REALTIME_MODEL}"


def _mulaw_to_pcm16(mulaw_b64: str) -> str:
    mulaw_bytes = base64.b64decode(mulaw_b64)
    pcm = audioop.ulaw2lin(mulaw_bytes, 2)
    return base64.b64encode(pcm).decode("ascii")


def _pcm16_to_mulaw(pcm_b64: str) -> str:
    pcm_bytes = base64.b64decode(pcm_b64)
    mulaw = audioop.lin2ulaw(pcm_bytes, 2)
    return base64.b64encode(mulaw).decode("ascii")


async def _openai_session(settings: VoiceSettings) -> Any:
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "OpenAI-Beta": "realtime=v1",
    }
    return await websockets.connect(REALTIME_URL, additional_headers=headers)


async def handle_twilio_stream(twilio_ws, session_id: str) -> None:
    settings = VoiceSettings.from_env()

    if not settings.openai_configured:
        await twilio_ws.close(code=1011, reason="OpenAI not configured")
        return

    stream_sid: str | None = None
    openai_ws = await _openai_session(settings)

    try:
        await openai_ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "modalities": ["text", "audio"],
                        "instructions": system_prompt(
                            settings.company_name,
                            settings.agent_name,
                        ),
                        "voice": "alloy",
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "input_audio_transcription": {"model": "whisper-1"},
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 500,
                        },
                    },
                }
            )
        )

        async def twilio_to_openai() -> None:
            nonlocal stream_sid
            async for message in twilio_ws:
                data = json.loads(message)
                event = data.get("event")

                if event == "start":
                    stream_sid = data["start"]["streamSid"]
                    logger.info("stream_started", extra={"session_id": session_id, "stream_sid": stream_sid})
                    await openai_ws.send(json.dumps({"type": "response.create"}))

                elif event == "media" and stream_sid:
                    payload = data["media"]["payload"]
                    pcm = _mulaw_to_pcm16(payload)
                    await openai_ws.send(
                        json.dumps({"type": "input_audio_buffer.append", "audio": pcm})
                    )

                elif event == "stop":
                    break

        async def openai_to_twilio() -> None:
            async for message in openai_ws:
                data = json.loads(message)
                event_type = data.get("type", "")

                if event_type == "response.audio.delta" and stream_sid:
                    pcm_delta = data.get("delta", "")
                    if pcm_delta:
                        mulaw = _pcm16_to_mulaw(pcm_delta)
                        await twilio_ws.send(
                            json.dumps(
                                {
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {"payload": mulaw},
                                }
                            )
                        )

                elif event_type == "response.audio.done" and stream_sid:
                    await twilio_ws.send(
                        json.dumps({"event": "mark", "streamSid": stream_sid, "mark": {"name": "done"}})
                    )

                elif event_type == "error":
                    logger.error("openai_realtime_error", extra={"error": data})

        await asyncio.gather(twilio_to_openai(), openai_to_twilio())

    except websockets.exceptions.ConnectionClosed:
        logger.info("stream_closed", extra={"session_id": session_id})
    finally:
        await openai_ws.close()
        await twilio_ws.close()


async def media_stream_handler(websocket) -> None:
    path = websocket.request.path if hasattr(websocket, "request") else ""
    session_id = "unknown"
    if "session_id=" in path:
        session_id = path.split("session_id=")[-1].split("&")[0]
    await handle_twilio_stream(websocket, session_id)


async def run_media_server(host: str = "0.0.0.0", port: int = 8765) -> None:
    logging.basicConfig(level=logging.INFO)
    async with websockets.serve(media_stream_handler, host, port):
        logger.info("media_stream_server_listening", extra={"host": host, "port": port})
        await asyncio.Future()
