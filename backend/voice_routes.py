from __future__ import annotations

import logging

from flask import Blueprint, Response, jsonify, request, send_file
from io import BytesIO

from backend.errors import ApiError
from pydantic import ValidationError

from voice_agent.agent import ConversationAgent
from voice_agent.config import VoiceSettings
from voice_agent import knowledge
from voice_agent.schemas import ChatRequest, ChatResponse, VoiceStatusResponse
from voice_agent.sessions import sessions
from voice_agent.twilio_handlers import call_status, handle_speech, incoming_call

logger = logging.getLogger(__name__)

voice_bp = Blueprint("voice", __name__)

_agent: ConversationAgent | None = None
_settings: VoiceSettings | None = None


def _get_settings() -> VoiceSettings:
    global _settings
    if _settings is None:
        _settings = VoiceSettings.from_env()
    return _settings


def _get_agent() -> ConversationAgent:
    global _agent
    if _agent is None:
        _agent = ConversationAgent(_get_settings())
    return _agent


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


@voice_bp.get("/status")
def voice_status():
    settings = _get_settings()
    agent = _get_agent()
    return jsonify(
        VoiceStatusResponse(
            openai_configured=settings.openai_configured,
            twilio_configured=settings.twilio_configured,
            company_name=settings.company_name,
            agent_name=settings.agent_name,
            greeting=agent.greeting(),
            sample_order_ids=list(knowledge.ORDERS.keys()),
        ).model_dump()
    )


@voice_bp.post("/chat")
def voice_chat():
    """Text chat endpoint for testing the agent without a phone call."""
    if not request.is_json:
        raise ApiError(400, "INVALID_JSON", "Request must be JSON.")
    req = _parse(ChatRequest, request.get_json(silent=True) or {})
    agent = _get_agent()

    if not agent.available:
        raise ApiError(
            503,
            "OPENAI_NOT_CONFIGURED",
            "Set OPENAI_API_KEY to use the voice agent.",
        )

    if req.session_id:
        session = sessions.get(req.session_id)
        if not session:
            session = sessions.create()
    else:
        session = sessions.create()

    result = agent.respond_to_user(req.message, session.history)
    session.history = result["history"]
    session.escalate = result["escalate"]

    return jsonify(
        ChatResponse(
            reply=result["reply"],
            session_id=session.session_id,
            escalate=result["escalate"],
        ).model_dump()
    )


@voice_bp.post("/chat/reset")
def reset_chat():
    if not request.is_json:
        raise ApiError(400, "INVALID_JSON", "Request must be JSON.")
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    if session_id:
        sessions.delete(session_id)
    new_session = sessions.create()
    return jsonify({"session_id": new_session.session_id, "message": "Session reset."})


@voice_bp.post("/tts")
def text_to_speech():
    """Generate speech audio from text (for web demo playback)."""
    if not request.is_json:
        raise ApiError(400, "INVALID_JSON", "Request must be JSON.")
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        raise ApiError(400, "VALIDATION_ERROR", "Field 'text' is required.")
    agent = _get_agent()
    if not agent.available:
        raise ApiError(503, "OPENAI_NOT_CONFIGURED", "Set OPENAI_API_KEY to use TTS.")
    audio = agent.text_to_speech(text[:4096])
    return send_file(BytesIO(audio), mimetype="audio/mpeg", download_name="speech.mp3")


# --- Twilio webhooks (no auth — validate via Twilio signature in production) ---


@voice_bp.post("/incoming")
def twilio_incoming():
    settings = _get_settings()
    agent = _get_agent()
    return incoming_call(settings, agent)


@voice_bp.post("/handle-speech")
def twilio_handle_speech():
    settings = _get_settings()
    agent = _get_agent()
    session_id = request.args.get("session_id", "")
    if not agent.available:
        response_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response><Say voice=\"Polly.Joanna\">"
            "Our virtual assistant is temporarily unavailable. Please try again later."
            "</Say><Hangup/></Response>"
        )
        return Response(response_xml, mimetype="text/xml")
    return handle_speech(settings, agent, session_id)


@voice_bp.post("/call-status")
def twilio_call_status():
    return call_status(_get_settings())
