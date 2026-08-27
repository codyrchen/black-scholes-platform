from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from flask import jsonify, request

logger = logging.getLogger(__name__)


@dataclass
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    details: Any | None = None


def _request_id() -> str:
    rid = request.headers.get("X-Request-Id")
    return rid or str(uuid.uuid4())


def handle_api_error(err: ApiError):
    rid = _request_id()
    payload = {
        "error": {
            "code": err.code,
            "message": err.message,
            "details": err.details,
            "request_id": rid,
        }
    }
    return jsonify(payload), err.status_code, {"X-Request-Id": rid}


def handle_uncaught_exception(err: Exception):
    rid = _request_id()
    logger.exception("uncaught_error", extra={"request_id": rid})
    payload = {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
            "request_id": rid,
        }
    }
    return jsonify(payload), 500, {"X-Request-Id": rid}

