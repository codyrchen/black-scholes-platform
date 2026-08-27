from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceSettings:
    openai_api_key: str
    openai_model: str
    openai_tts_voice: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    company_name: str
    agent_name: str
    public_url: str
    voice_ws_public_url: str
    human_transfer_number: str
    use_realtime_stream: bool

    @staticmethod
    def from_env() -> VoiceSettings:
        public_url = os.getenv("PUBLIC_URL", "http://localhost:5001")
        return VoiceSettings(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            openai_tts_voice=os.getenv("OPENAI_TTS_VOICE", "nova"),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER", ""),
            company_name=os.getenv("COMPANY_NAME", "Black-Scholes Platform"),
            agent_name=os.getenv("AGENT_NAME", "Alex"),
            public_url=public_url,
            voice_ws_public_url=os.getenv("VOICE_WS_PUBLIC_URL", "ws://localhost:8765"),
            human_transfer_number=os.getenv("HUMAN_TRANSFER_NUMBER", ""),
            use_realtime_stream=os.getenv("VOICE_USE_REALTIME", "false").lower() == "true",
        )

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def twilio_configured(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token)
