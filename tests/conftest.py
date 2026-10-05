import pytest

from backend import create_app
from backend.config import Settings


@pytest.fixture
def client():
    settings = Settings(port=0, host="127.0.0.1", api_prefix="/api/v1", cors_origins=["*"])
    return create_app(settings).test_client()
