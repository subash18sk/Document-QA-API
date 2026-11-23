import pytest

from app.config import settings
from app.models import Chunk
from tests.conftest import upload

PROTECTED = [("get", "/documents"), ("post", "/documents"), ("get", "/documents/1"),
             ("post", "/documents/1/ask"), ("delete", "/documents/1")]


@pytest.mark.parametrize("method,path", PROTECTED)
def test_every_document_route_requires_a_token(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_upload_pdf_indexes_pages_and_chunks(client, auth, sample_doc):
    assert sample_doc["filename"] == "lumenbay-hr-policy.pdf"
    assert sample_doc["page_count"] == 4
    assert sample_doc["chunk_count"] >= 4
    assert sample_doc["embedding_model"] == "hash-1024"


def test_upload_plain_text_with_page_breaks(client, auth):
    text = "Office hours are 9 to 5.\fThe cafeteria serves lunch from 12 to 2 PM."
    r = upload(client, auth, name="notes.txt", content=text.encode(), mime="text/plain")
    assert r.status_code == 201 and r.json()["page_count"] == 2
    a = client.post(f"/documents/{r.json()['id']}/ask", json={"question": "When is lunch served?"}, headers=auth).json()
    assert a["found"] and "12 to 2 PM" in a["answer"] and a["sources"][0]["page"] == 2


@pytest.mark.parametrize("name,content,expected", [
    ("photo.png", b"\x89PNG....", 415),          # unsupported type
    ("empty.pdf", b"", 422),                      # empty file
    ("fake.pdf", b"this is not a pdf", 422),      # wrong content for the extension
    ("blank.txt", b"   \n\n  ", 422),             # nothing extractable
    ("latin1.txt", "café".encode("latin-1"), 422),  # not UTF-8
])
def test_bad_uploads_are_rejected_clearly(client, auth, name, content, expected):
    r = upload(client, auth, name=name, content=content)
    assert r.status_code == expected
    assert r.json()["detail"]


def test_oversized_upload_is_rejected(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 0.001)  # ~1 KB
    r = upload(client, auth, name="big.txt", content=b"word " * 1000, mime="text/plain")
    assert r.status_code == 413


def test_list_and_get_documents(client, auth, sample_doc):
    listed = client.get("/documents", headers=auth).json()
    assert [d["id"] for d in listed] == [sample_doc["id"]]
    assert client.get(f"/documents/{sample_doc['id']}", headers=auth).json()["filename"] == sample_doc["filename"]


def test_other_users_cannot_see_ask_or_delete(client, auth, other_auth, sample_doc):
    doc_id = sample_doc["id"]
    assert client.get("/documents", headers=other_auth).json() == []
    assert client.get(f"/documents/{doc_id}", headers=other_auth).status_code == 404
    assert client.post(f"/documents/{doc_id}/ask", json={"question": "How many paid leave days?"},
                       headers=other_auth).status_code == 404
    assert client.delete(f"/documents/{doc_id}", headers=other_auth).status_code == 404
    assert client.get(f"/documents/{doc_id}", headers=auth).status_code == 200  # owner unaffected


def test_delete_removes_document_and_its_vectors(client, auth, sample_doc, db_session):
    doc_id = sample_doc["id"]
    assert db_session.query(Chunk).filter(Chunk.document_id == doc_id).count() == sample_doc["chunk_count"]
    assert client.delete(f"/documents/{doc_id}", headers=auth).status_code == 204
    assert client.get(f"/documents/{doc_id}", headers=auth).status_code == 404
    db_session.expire_all()
    assert db_session.query(Chunk).filter(Chunk.document_id == doc_id).count() == 0
