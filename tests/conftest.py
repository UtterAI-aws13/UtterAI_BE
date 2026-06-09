"""Shared pytest fixtures for UtterAI BE tests.

Integration tests require PostgreSQL running:
  docker compose -f docker-compose.local.yml up -d
  createdb -U utterai utterai_test  (최초 1회)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.api.dependencies import get_db_session
from app.models.base import Base
from app.models import entities  # noqa: F401 — registers all ORM models

TEST_DATABASE_URL = (
    "postgresql+psycopg://utterai:utterai@localhost:5432/utterai"
)

# ── DB fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """각 테스트마다 트랜잭션을 열고, 테스트 후 롤백해 DB를 깨끗이 유지한다."""
    connection = test_engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(
        bind=connection, autocommit=False, autoflush=False
    )
    session = TestSession()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ── HTTP client fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def client(db_session):
    """DB 의존성이 테스트 세션으로 교체된 TestClient."""
    def _override():
        yield db_session

    app.dependency_overrides[get_db_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Auth fixtures ────────────────────────────────────────────────────────────

TEST_USER = {
    "email": "testuser@example.com",
    "password": "TestPass1!",
    "name": "Test User",
}


@pytest.fixture
def auth_headers(client):
    """테스트 유저를 생성하고 Authorization 헤더를 반환한다."""
    client.post("/api/v1/auth/signup", json=TEST_USER)
    res = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
