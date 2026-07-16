from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path(__file__).parent / "test.sqlite3"
os.environ["CDB_DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["CDB_API_TOKEN"] = "test-token"
os.environ["CDB_PUBLIC_BASE_URL"] = "http://testserver"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}
