from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    escalate: bool = False


class VoiceStatusResponse(BaseModel):
    openai_configured: bool
    twilio_configured: bool
    company_name: str
    agent_name: str
    greeting: str
    sample_order_ids: list[str]
