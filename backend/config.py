from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    port: int
    host: str
    api_prefix: str
    cors_origins: list[str]

    @staticmethod
    def from_env() -> "Settings":
        port = int(os.getenv("PORT", "5001"))
        host = os.getenv("HOST", "0.0.0.0")
        api_prefix = os.getenv("API_PREFIX", "/api/v1")
        cors = os.getenv("CORS_ORIGINS", "*").strip()
        cors_origins = ["*"] if cors == "*" else [o.strip() for o in cors.split(",") if o.strip()]
        return Settings(port=port, host=host, api_prefix=api_prefix, cors_origins=cors_origins)

