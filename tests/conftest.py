"""
Shared fixtures. Every test gets a fresh in-memory database and the offline providers
(hash embeddings + extractive answers), so the suite needs no network and no API keys.
"""
import pathlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.rag.answer import ExtractiveAnswerer
from app.rag.embeddings import HashEmbedder
from app.rag.providers import get_answerer, get_embedder

SAMPLE_PDF = pathlib.Path(__file__).resolve().parent.parent / "sample_docs" / "lumenbay-hr-policy.pdf"


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(eng, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture()
def db_session(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    s = Session()
    yield s
    s.close()


@pytest.fixture()
def client(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_embedder] = lambda: HashEmbedder(1024)
    app.dependency_overrides[get_answerer] = lambda: ExtractiveAnswerer()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client, email: str, password: str = "secret123") -> dict:
    client.post("/auth/signup", json={"email": email, "password": password})
    token = client.post("/auth/login", data={"username": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth(client):
    return login(client, "arjun@example.com")


@pytest.fixture()
def other_auth(client):
    return login(client, "priya@example.com")


def upload(client, headers, path=SAMPLE_PDF, name=None, content=None, mime="application/pdf"):
    data = content if content is not None else pathlib.Path(path).read_bytes()
    return client.post("/documents", files={"file": (name or pathlib.Path(path).name, data, mime)}, headers=headers)


@pytest.fixture()
def sample_doc(client, auth):
    r = upload(client, auth)
    assert r.status_code == 201, r.text
    return r.json()
