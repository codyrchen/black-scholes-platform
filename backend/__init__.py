from __future__ import annotations

from flask import Flask, jsonify
from flask_cors import CORS
from spectree import SpecTree

from backend.config import Settings
from backend.errors import ApiError, handle_api_error, handle_uncaught_exception
from backend.routes import api_v1, calculate_payoff_v1, calculate_price_v1


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings.from_env()

    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    CORS(app, resources={r"/api/*": {"origins": settings.cors_origins}})

    # OpenAPI docs
    spec = SpecTree(
        "flask",
        title="Black-Scholes Platform API",
        version="1.0.0",
        path=f"{settings.api_prefix}/docs",
    )
    spec.register(app)

    # Errors
    app.register_error_handler(ApiError, handle_api_error)
    app.register_error_handler(Exception, handle_uncaught_exception)

    # Routes
    app.register_blueprint(api_v1, url_prefix=settings.api_prefix)

    # Legacy (non-versioned) routes kept for compatibility with existing frontend.
    # These call through to the v1 implementation.
    app.add_url_rule("/api/price", view_func=calculate_price_v1, methods=["POST"])
    app.add_url_rule("/api/payoff", view_func=calculate_payoff_v1, methods=["POST"])

    @app.get("/api/health")
    @app.get(f"{settings.api_prefix}/health")
    def health_check():
        return jsonify({"status": "ok", "message": "Backend is running"})

    return app
