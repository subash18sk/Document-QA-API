"""
Tables:
- users      who can log in
- documents  one row per uploaded file, owned by a user
- chunks     the searchable pieces of a document: text, page number and its embedding vector

Embeddings are stored as raw float32 bytes in the database, next to the chunk text, so a single
database holds everything and deleting a document deletes its vectors with it (ON DELETE CASCADE).
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    page_count = Column(Integer, nullable=False)
    chunk_count = Column(Integer, nullable=False, default=0)
    # Which embedding model produced this document's vectors. Questions must be embedded
    # with the same model, otherwise similarity scores are meaningless.
    embedding_model = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    owner = relationship("User", back_populates="documents")
    chunks = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan", passive_deletes=True,
        order_by="Chunk.position",
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False)       # order within the document
    page = Column(Integer, nullable=False)           # 1-based page number, for citations
    text = Column(Text, nullable=False)
    embedding = Column(LargeBinary, nullable=False)  # float32 vector as bytes

    document = relationship("Document", back_populates="chunks")
