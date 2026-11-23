"""
The two RAG flows, kept free of HTTP concerns so they are easy to test and reason about.

index_document:   file bytes -> pages -> chunks -> embeddings -> stored rows
answer_question:  question -> embedding -> top-k passages -> similarity gate -> answer + sources
"""
import os

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Chunk, Document, User
from app.rag.answer import NOT_FOUND_MESSAGE, Passage
from app.rag.chunking import chunk_pages
from app.rag.extract import SUPPORTED_EXTENSIONS, extract_pages
from app.rag.store import search, to_bytes
from app.schemas import AskResponse, Source


class EmbeddingModelMismatch(RuntimeError):
    """The document was indexed with a different embedding model than the one configured now."""


def index_document(db: Session, user: User, filename: str, data: bytes, embedder) -> Document:
    safe_name = os.path.basename(filename or "upload")[:255]
    pages = extract_pages(safe_name, data)
    chunks = chunk_pages(pages, settings.chunk_words, settings.chunk_overlap)
    vectors = embedder.embed([c.text for c in chunks])

    ext = os.path.splitext(safe_name.lower())[1]
    doc = Document(
        user_id=user.id,
        filename=safe_name,
        content_type=SUPPORTED_EXTENSIONS[ext],
        size_bytes=len(data),
        page_count=len(pages),
        chunk_count=len(chunks),
        embedding_model=embedder.name,
    )
    db.add(doc)
    db.flush()  # assigns doc.id without committing yet
    db.add_all(
        Chunk(document_id=doc.id, position=i, page=c.page, text=c.text, embedding=to_bytes(v))
        for i, (c, v) in enumerate(zip(chunks, vectors))
    )
    db.commit()  # document and all its chunks are saved together, or not at all
    db.refresh(doc)
    return doc


def answer_question(db: Session, doc: Document, question: str, top_k: int | None,
                    embedder, answerer) -> AskResponse:
    if embedder.name != doc.embedding_model:
        raise EmbeddingModelMismatch(
            f"This document was indexed with '{doc.embedding_model}' but the server now uses "
            f"'{embedder.name}'. Re-upload the document to re-index it."
        )
    query_vector = embedder.embed([question])[0]
    hits = search(db, doc.id, query_vector, top_k or settings.top_k)

    # Gate 1: if even the closest passage is far from the question, don't ask the model at all.
    if not hits or hits[0].score < settings.similarity_threshold:
        return AskResponse(question=question, answer=NOT_FOUND_MESSAGE, found=False,
                           sources=[], answered_by="similarity-threshold")

    # Gate 2: the answerer itself must confirm the passages contain the answer.
    result = answerer.answer(question, [Passage(h.chunk.page, h.chunk.text) for h in hits])
    sources = [
        Source(chunk_id=h.chunk.id, page=h.chunk.page, score=round(h.score, 4), text=h.chunk.text)
        for h in hits
    ] if result.found else []
    return AskResponse(question=question, answer=result.text, found=result.found,
                       sources=sources, answered_by=answerer.name)
