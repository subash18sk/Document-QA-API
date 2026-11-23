"""Pydantic schemas: the exact shapes accepted and returned by the API."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---------- auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- documents ----------
class DocumentOut(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int
    page_count: int
    chunk_count: int
    embedding_model: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- questions ----------
class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    top_k: int | None = Field(default=None, ge=1, le=10, description="How many passages to retrieve (default from settings)")


class Source(BaseModel):
    chunk_id: int
    page: int
    score: float = Field(description="Cosine similarity between the question and this passage (higher = closer)")
    text: str


class AskResponse(BaseModel):
    question: str
    answer: str
    found: bool = Field(description="False when the document does not contain the answer")
    sources: list[Source]
    answered_by: str = Field(description="Which answer generator produced the answer")
