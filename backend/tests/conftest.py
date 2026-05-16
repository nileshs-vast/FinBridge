import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://finbridge:finbridge@localhost:5432/finbridge_test",
)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("EXTRACTION_PROVIDER", "fixture")


@pytest.fixture()
def client() -> TestClient:
    from app.main import create_app

    return TestClient(create_app())
