"""
Vector storage and search.

Vectors live in the `chunks` table as float32 bytes. A question is answered against ONE document,
so search loads just that document's vectors (hundreds, not millions) and ranks them with a single
matrix product. That keeps the whole system in one database with no extra service to run.
At larger scale the same interface can sit on pgvector, Chroma or FAISS instead.
"""
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from app.models import Chunk


def to_bytes(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


@dataclass
class Hit:
    chunk: Chunk
    score: float


def search(db: Session, document_id: int, query_vector: np.ndarray, top_k: int) -> list[Hit]:
    rows = db.query(Chunk.id, Chunk.embedding).filter(Chunk.document_id == document_id).all()
    if not rows:
        return []
    matrix = np.frombuffer(b"".join(r.embedding for r in rows), dtype=np.float32).reshape(len(rows), -1)
    if matrix.shape[1] != query_vector.shape[0]:
        raise ValueError("Question and document embeddings have different dimensions.")
    scores = matrix @ query_vector.astype(np.float32)          # cosine similarity (rows are unit length)
    best = np.argsort(-scores)[:top_k]
    ids = [rows[i].id for i in best]
    chunks = {c.id: c for c in db.query(Chunk).filter(Chunk.id.in_(ids)).all()}
    return [Hit(chunks[rows[i].id], float(scores[i])) for i in best]
