from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CallSession:
    session_id: str
    call_sid: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    escalate: bool = False


class SessionStore:
    """Thread-safe in-memory session store for active calls."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._sessions: dict[str, CallSession] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def create(self, call_sid: str | None = None) -> CallSession:
        session_id = str(uuid.uuid4())
        session = CallSession(session_id=session_id, call_sid=call_sid)
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> CallSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session and time.time() - session.created_at > self._ttl:
                del self._sessions[session_id]
                return None
            return session

    def get_by_call_sid(self, call_sid: str) -> CallSession | None:
        with self._lock:
            for session in self._sessions.values():
                if session.call_sid == call_sid:
                    return session
        return None

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


# Shared store used by HTTP routes and Twilio webhooks.
sessions = SessionStore()
