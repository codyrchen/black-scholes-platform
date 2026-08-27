from __future__ import annotations

import logging
from urllib.parse import urljoin

from flask import Response, request
from twilio.twiml.voice_response import Connect, Gather, VoiceResponse

from voice_agent.agent import ConversationAgent
from voice_agent.config import VoiceSettings
from voice_agent.sessions import sessions

logger = logging.getLogger(__name__)

def _public_url(settings: VoiceSettings, path: str) -> str:
    base = settings.public_url.rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


def incoming_call(settings: VoiceSettings, agent: ConversationAgent) -> Response:
    """Twilio webhook: answer an incoming call."""
    call_sid = request.values.get("CallSid", "")
    session = sessions.create(call_sid=call_sid)

    response = VoiceResponse()
    greeting = agent.greeting()

    if settings.use_realtime_stream:
        connect = Connect()
        base = settings.voice_ws_public_url.rstrip("/")
        stream_url = f"{base}?session_id={session.session_id}"
        connect.stream(url=stream_url)
        response.append(connect)
        response.say(greeting, voice="Polly.Joanna")
    else:
        gather = Gather(
            input="speech",
            action=_public_url(settings, f"/api/v1/voice/handle-speech?session_id={session.session_id}"),
            method="POST",
            speech_timeout="auto",
            language="en-US",
            hints="order, billing, refund, cancel, account, support, ORD",
        )
        gather.say(greeting, voice="Polly.Joanna")
        response.append(gather)
        response.say("I didn't hear anything. Goodbye!", voice="Polly.Joanna")
        response.hangup()

    return Response(str(response), mimetype="text/xml")


def handle_speech(settings: VoiceSettings, agent: ConversationAgent, session_id: str) -> Response:
    """Twilio webhook: process caller speech and respond."""
    session = sessions.get(session_id)
    if not session:
        session = sessions.create(call_sid=request.values.get("CallSid"))

    speech = (request.values.get("SpeechResult") or "").strip()
    confidence = request.values.get("Confidence", "0")

    logger.info(
        "speech_received",
        extra={"session_id": session_id, "speech": speech, "confidence": confidence},
    )

    response = VoiceResponse()

    if not speech:
        gather = _make_gather(settings, session.session_id)
        gather.say("I'm sorry, I didn't catch that. Could you please repeat?", voice="Polly.Joanna")
        response.append(gather)
        return Response(str(response), mimetype="text/xml")

    try:
        result = agent.respond_to_user(speech, session.history)
        session.history = result["history"]
        session.escalate = result["escalate"]
        reply = result["reply"]
    except Exception:
        logger.exception("agent_error", extra={"session_id": session_id})
        reply = "I'm sorry, I'm having technical difficulties. Let me transfer you to a team member."
        session.escalate = True

    if session.escalate:
        response.say(reply, voice="Polly.Joanna")
        human = settings.human_transfer_number or None
        if human:
            response.dial(human)
        else:
            response.say(
                "A support ticket has been created and someone will call you back shortly. Goodbye!",
                voice="Polly.Joanna",
            )
            response.hangup()
        return Response(str(response), mimetype="text/xml")

    gather = _make_gather(settings, session.session_id)
    gather.say(reply, voice="Polly.Joanna")
    response.append(gather)
    response.say("Are you still there? Goodbye!", voice="Polly.Joanna")
    response.hangup()

    return Response(str(response), mimetype="text/xml")


def _make_gather(settings: VoiceSettings, session_id: str) -> Gather:
    return Gather(
        input="speech",
        action=_public_url(settings, f"/api/v1/voice/handle-speech?session_id={session_id}"),
        method="POST",
        speech_timeout="auto",
        language="en-US",
        hints="order, billing, refund, cancel, account, support, ORD, yes, no, thank you",
    )


def call_status(settings: VoiceSettings) -> Response:
    """Twilio status callback — log call lifecycle events."""
    call_sid = request.values.get("CallSid", "")
    status = request.values.get("CallStatus", "")
    logger.info("call_status", extra={"call_sid": call_sid, "status": status})

    session = sessions.get_by_call_sid(call_sid)
    if session and status in ("completed", "failed", "busy", "no-answer", "canceled"):
        sessions.delete(session.session_id)

    return Response("", status=204)
