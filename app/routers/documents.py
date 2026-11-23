"""
Document routes. Every query is scoped to the logged-in user: someone else's document id returns
404, exactly as if it didn't exist.
"""
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Document, User
from app.rag.embeddings import ProviderError
from app.rag.extract import ExtractionError, UnsupportedFileType
from app.rag.pipeline import EmbeddingModelMismatch, answer_question, index_document
from app.rag.providers import get_answerer, get_embedder
from app.schemas import AskRequest, AskResponse, DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])


def _owned_or_404(db: Session, doc_id: int, user: User) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user.id).first()
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return doc


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(..., description="A PDF, .txt or .md file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedder=Depends(get_embedder),
):
    """Upload a document. It is extracted, chunked, embedded and stored before this returns."""
    # Read at most limit+1 bytes: enough to detect an oversized file without loading all of it.
    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"File is larger than {settings.max_upload_mb:g} MB.")
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The uploaded file is empty.")
    try:
        return index_document(db, current_user, file.filename, data, embedder)
    except UnsupportedFileType as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc))
    except ExtractionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    except ProviderError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (db.query(Document).filter(Document.user_id == current_user.id)
            .order_by(Document.created_at.desc(), Document.id.desc()).all())


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _owned_or_404(db, doc_id, current_user)


@router.post("/{doc_id}/ask", response_model=AskResponse)
def ask(
    doc_id: int,
    payload: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedder=Depends(get_embedder),
    answerer=Depends(get_answerer),
):
    """Ask a question about one of your documents. Answers cite the passages they came from."""
    doc = _owned_or_404(db, doc_id, current_user)
    try:
        return answer_question(db, doc, payload.question.strip(), payload.top_k, embedder, answerer)
    except EmbeddingModelMismatch as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except ProviderError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete a document together with all of its chunks and vectors."""
    doc = _owned_or_404(db, doc_id, current_user)
    db.delete(doc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
