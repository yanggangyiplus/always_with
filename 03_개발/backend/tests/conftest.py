import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import invites
from app.db import models  # noqa: F401
from app.db.session import Base, get_db
from app.main import app


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, autoflush=False)()
    app.dependency_overrides[get_db] = lambda: s
    invites._fails.clear()
    yield s
    app.dependency_overrides.clear()


@pytest.fixture
def client(db):
    return TestClient(app)


def signup(client, email, role):
    r = client.post("/api/auth/register", json={"email": email, "password": "password1", "role": role})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def guardian(client):
    return signup(client, "g@x.com", "guardian")


@pytest.fixture
def parent(client):
    return signup(client, "p@x.com", "parent")
