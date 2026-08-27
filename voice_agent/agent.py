from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from voice_agent.config import VoiceSettings
from voice_agent.prompts import system_prompt
from voice_agent.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


class ConversationAgent:
    """OpenAI-powered customer service agent with tool calling."""

    def __init__(self, settings: VoiceSettings | None = None) -> None:
        self.settings = settings or VoiceSettings.from_env()
        self._client: OpenAI | None = None
        if self.settings.openai_configured:
            self._client = OpenAI(api_key=self.settings.openai_api_key)

    @property
    def available(self) -> bool:
        return self._client is not None

    def _ensure_client(self) -> OpenAI:
        if not self._client:
            raise RuntimeError(
                "OpenAI API key not configured. Set OPENAI_API_KEY in your environment."
            )
        return self._client

    def respond(
        self,
        messages: list[dict[str, Any]],
        *,
        include_system: bool = True,
    ) -> dict[str, Any]:
        """Generate the next agent response given conversation history."""
        client = self._ensure_client()
        full_messages: list[dict[str, Any]] = []
        if include_system:
            full_messages.append(
                {
                    "role": "system",
                    "content": system_prompt(
                        self.settings.company_name,
                        self.settings.agent_name,
                    ),
                }
            )
        full_messages.extend(messages)

        escalate = False
        for _ in range(MAX_TOOL_ROUNDS):
            response = client.chat.completions.create(
                model=self.settings.openai_model,
                messages=full_messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
            choice = response.choices[0]
            message = choice.message

            if message.tool_calls:
                full_messages.append(message.model_dump())
                for tool_call in message.tool_calls:
                    args = json.loads(tool_call.function.arguments or "{}")
                    result = execute_tool(tool_call.function.name, args)
                    if result.get("escalate"):
                        escalate = True
                    full_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result),
                        }
                    )
                continue

            text = (message.content or "").strip()
            return {
                "reply": text,
                "escalate": escalate,
                "messages": full_messages,
            }

        return {
            "reply": "I'm having trouble processing that. Let me connect you with a specialist.",
            "escalate": True,
            "messages": full_messages,
        }

    def respond_to_user(self, user_text: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        messages = list(history) + [{"role": "user", "content": user_text}]
        result = self.respond(messages, include_system=True)
        updated_history = messages + [{"role": "assistant", "content": result["reply"]}]
        return {
            "reply": result["reply"],
            "escalate": result["escalate"],
            "history": updated_history,
        }

    def greeting(self) -> str:
        return (
            f"Hi, thanks for calling {self.settings.company_name}. "
            f"My name is {self.settings.agent_name}, your virtual assistant. "
            "How can I help you today?"
        )

    def text_to_speech(self, text: str) -> bytes:
        """Generate speech audio (mp3) via OpenAI TTS."""
        client = self._ensure_client()
        response = client.audio.speech.create(
            model="tts-1",
            voice=self.settings.openai_tts_voice,  # type: ignore[arg-type]
            input=text,
            response_format="mp3",
        )
        return response.content
