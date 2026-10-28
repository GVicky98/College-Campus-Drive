"""Test fixtures: a fresh in-memory SQLite database (or TEST_DATABASE_URL) with reference + demo data per test."""
import os

os.environ["APP_ENV"] = "testing"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-long-enough-123456")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-123456")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import database, ratelimit  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402
import app.models  # noqa: E402,F401

PASSWORD = "Demo@1234"


@pytest.fixture()
def db_engine():
    get_settings.cache_clear()
    engine = database.init_engine(os.environ.get("TEST_DATABASE_URL") or "sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    from app.seed import seed_reference
    from app.seed_demo import seed_demo
    with database.SessionLocal() as db:
        seed_reference(db)
        seed_demo(db, PASSWORD)
    ratelimit.reset()
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db(db_engine):
    with database.SessionLocal() as session:
        yield session


@pytest.fixture()
def client(db_engine):
    from app.main import create_app
    return TestClient(create_app(), base_url="http://testserver")


def login(client, email: str, password: str = PASSWORD) -> dict:
    r = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def student(client):
    return login(client, "student@campus.demo")


@pytest.fixture()
def faculty(client):
    return login(client, "faculty@campus.demo")


@pytest.fixture()
def admin(client):
    return login(client, "admin@campus.demo")
