"""Unit tests for the individual RAG building blocks."""
import httpx
import numpy as np
import pytest

from app.rag.chunking import chunk_pages
from app.rag.embeddings import HashEmbedder, OpenAICompatEmbedder, ProviderError
from app.rag.extract import ExtractionError, Page, UnsupportedFileType, extract_pages
from app.rag.text import sentences, stem, tokenize


def test_chunks_overlap_and_never_cross_pages():
    words = [f"w{i}" for i in range(25)]
    chunks = chunk_pages([Page(1, " ".join(words)), Page(2, "short page")], size=10, overlap=3)
    # 25 words, window 10, step 7 -> windows start at words 0, 7, 14, 21
    assert [c.page for c in chunks] == [1, 1, 1, 1, 2]
    first, second = chunks[0].text.split(), chunks[1].text.split()
    assert first[-3:] == second[:3]                  # 3-word overlap
    assert chunks[3].text.split()[-1] == "w24"       # nothing dropped at the end
    assert chunks[4].text == "short page"


@pytest.mark.parametrize("size,overlap", [(0, 0), (10, 10), (10, -1)])
def test_invalid_chunk_settings(size, overlap):
    with pytest.raises(ValueError):
        chunk_pages([Page(1, "a b c")], size, overlap)


def test_hash_embedder_is_deterministic_normalised_and_meaningful():
    emb = HashEmbedder(256)
    a, b, c = emb.embed(["paid leave per year", "paid leave per year", "the cafeteria menu"])
    assert np.allclose(a, b)                                 # same text -> same vector, across calls
    assert np.isclose(np.linalg.norm(a), 1.0, atol=1e-5)     # unit length -> dot product = cosine
    q = emb.embed(["how many days of paid leave"])[0]
    assert q @ a > q @ c                                     # related text scores higher


def test_openai_compatible_embedder_batches_and_orders_results():
    seen = []

    def handler(req: httpx.Request):
        import json
        body = json.loads(req.content)
        seen.append(len(body["input"]))
        data = [{"index": i, "embedding": [float(i + 1), 0.0]} for i in range(len(body["input"]))]
        return httpx.Response(200, json={"data": list(reversed(data))})  # out of order on purpose

    emb = OpenAICompatEmbedder("https://emb.test/v1", "k", "m", batch_size=2,
                               client=httpx.Client(transport=httpx.MockTransport(handler)))
    out = emb.embed(["a", "b", "c"])
    assert seen == [2, 1] and out.shape == (3, 2) and emb.name == "openai:m"
    assert np.allclose(np.linalg.norm(out, axis=1), 1.0)


def test_openai_compatible_providers_need_a_key():
    with pytest.raises(ProviderError):
        OpenAICompatEmbedder("https://x", None, "m")


def test_extraction_errors():
    with pytest.raises(UnsupportedFileType):
        extract_pages("a.docx", b"PK..")
    with pytest.raises(ExtractionError):
        extract_pages("a.pdf", b"not a pdf")


def test_headings_become_their_own_sentence():
    pages = extract_pages("doc.md", b"## Leave Policy\nEmployees get 18 days of paid leave.\nSick leave is 12 days.")
    assert sentences(pages[0].text) == ["Leave Policy:", "Employees get 18 days of paid leave.", "Sick leave is 12 days."]


@pytest.mark.parametrize("words", [("reimburse", "reimbursed", "reimburses"), ("employee", "employees"),
                                   ("leave", "leaves"), ("policy", "policies"), ("work", "working")])
def test_stemming_maps_word_forms_together(words):
    assert len({stem(w) for w in words}) == 1


def test_tokenize_drops_question_words():
    assert tokenize("How many days do I get?") == ["day"]
