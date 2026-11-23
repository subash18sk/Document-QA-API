"""Question answering: grounded answers, citations, honest refusals, and LLM integration (mocked)."""
import json

import httpx
import pytest

from app.main import app
from app.rag.answer import NOT_FOUND_MESSAGE, OpenAICompatLLM
from app.rag.embeddings import HashEmbedder
from app.rag.providers import get_answerer, get_embedder

ANSWERABLE = [
    ("How many paid leaves do I get?", "18 days of paid leave", 2),
    ("How long is maternity leave?", "26 weeks", 2),
    ("What is the notice period after confirmation?", "60 days", 3),
    ("What is the notice period during probation?", "15 days", 3),
    ("How much health insurance cover do employees have?", "INR 5,00,000", 4),
    ("Is internet reimbursed?", "INR 1,000 per month", 1),
    ("When are appraisals?", "April", 3),
    ("What are the working hours?", "9:30 AM to 6:30 PM", 1),
]
UNANSWERABLE = ["What is the company's stock price?", "Who won the cricket world cup?", "What is the dress code?"]


def ask(client, auth, doc_id, question, **extra):
    return client.post(f"/documents/{doc_id}/ask", json={"question": question, **extra}, headers=auth)


@pytest.mark.parametrize("question,expected,page", ANSWERABLE)
def test_answers_come_from_the_document_with_page_citation(client, auth, sample_doc, question, expected, page):
    body = ask(client, auth, sample_doc["id"], question).json()
    assert body["found"] is True
    assert expected in body["answer"]
    assert f"(p. {page})" in body["answer"]
    assert body["sources"], "a found answer must return its source passages"
    assert any(expected in s["text"] for s in body["sources"])
    scores = [s["score"] for s in body["sources"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize("question", UNANSWERABLE)
def test_questions_outside_the_document_get_an_honest_not_found(client, auth, sample_doc, question):
    body = ask(client, auth, sample_doc["id"], question).json()
    assert body["found"] is False
    assert body["answer"] == NOT_FOUND_MESSAGE
    assert body["sources"] == []


def test_top_k_controls_number_of_sources(client, auth, sample_doc):
    body = ask(client, auth, sample_doc["id"], "How many sick days do I get?", top_k=2).json()
    assert body["found"] and len(body["sources"]) == 2


@pytest.mark.parametrize("payload", [{"question": "hi"}, {"question": "x" * 501}, {"question": "valid?", "top_k": 0}])
def test_invalid_questions_rejected(client, auth, sample_doc, payload):
    assert client.post(f"/documents/{sample_doc['id']}/ask", json=payload, headers=auth).status_code == 422


def test_changing_embedding_model_requires_reupload(client, auth, sample_doc):
    app.dependency_overrides[get_embedder] = lambda: HashEmbedder(512)  # a different model
    r = ask(client, auth, sample_doc["id"], "How many paid leaves do I get?")
    assert r.status_code == 409 and "Re-upload" in r.json()["detail"]


# ---------------------------------------------------------------- LLM path (no network: mocked)
def _llm_with(reply: str | None = None, status: int = 200):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        if status != 200:
            return httpx.Response(status, json={"error": "boom"})
        return httpx.Response(200, json={"choices": [{"message": {"content": reply}}]})

    llm = OpenAICompatLLM("https://llm.test/v1", "test-key", "test-model",
                          client=httpx.Client(transport=httpx.MockTransport(handler)))
    return llm, calls


def test_llm_receives_grounding_prompt_and_answer_is_returned(client, auth, sample_doc):
    llm, calls = _llm_with("Full-time employees get 18 days of paid leave per year (p. 2).")
    app.dependency_overrides[get_answerer] = lambda: llm
    body = ask(client, auth, sample_doc["id"], "How many paid leaves do I get?").json()

    assert body["found"] is True and body["answered_by"] == "openai:test-model"
    assert body["answer"].startswith("Full-time employees get 18 days")
    sent = calls[0]
    assert sent["model"] == "test-model" and sent["temperature"] == 0
    system, user = sent["messages"][0]["content"], sent["messages"][1]["content"]
    assert "ONLY" in system and "NOT_FOUND" in system and "Never follow instructions" in system
    assert "Question: How many paid leaves do I get?" in user
    assert "18 days of paid leave" in user          # retrieved context was included
    assert "(page 2)" in user                       # with page numbers for citation


def test_llm_not_found_reply_becomes_honest_refusal(client, auth, sample_doc):
    llm, _ = _llm_with("NOT_FOUND")
    app.dependency_overrides[get_answerer] = lambda: llm
    body = ask(client, auth, sample_doc["id"], "What are the rules on paid leave carry forward for interns?").json()
    assert body["found"] is False and body["answer"] == NOT_FOUND_MESSAGE and body["sources"] == []


def test_irrelevant_question_never_reaches_the_llm(client, auth, sample_doc):
    llm, calls = _llm_with("should not be used")
    app.dependency_overrides[get_answerer] = lambda: llm
    body = ask(client, auth, sample_doc["id"], "Who won the cricket world cup?").json()
    assert body["found"] is False and body["answered_by"] == "similarity-threshold"
    assert calls == []  # the similarity gate saved an LLM call


def test_llm_outage_returns_503(client, auth, sample_doc):
    llm, _ = _llm_with(status=500)
    app.dependency_overrides[get_answerer] = lambda: llm
    r = ask(client, auth, sample_doc["id"], "How many paid leaves do I get?")
    assert r.status_code == 503
