from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

load_dotenv()

from backend import create_app
from backend.config import Settings
from backend.logging_config import configure_logging


def main() -> None:
    settings = Settings.from_env()
    configure_logging()
    app = create_app(settings)

    logging.getLogger(__name__).info(
        "starting_server",
        extra={"host": settings.host, "port": settings.port, "api_prefix": settings.api_prefix},
    )

    app.run(debug=False, port=settings.port, host=settings.host)


if __name__ == "__main__":
    main()