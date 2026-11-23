"""
Document Q&A API — upload a document, ask questions, get answers grounded in it, with sources.

Run locally:  uvicorn app.main:app --reload
  Web app (for everyone):        http://127.0.0.1:8000/
  Interactive API docs (devs):   http://127.0.0.1:8000/docs
"""
import pathlib

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse

from app import models  # noqa: F401  (registers tables)
from app.database import init_db
from app.rag.providers import get_answerer, get_embedder
from app.routers import auth, documents

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB_PAGE = ROOT / "app" / "web" / "index.html"
SAMPLE_PDF = ROOT / "sample_docs" / "lumenbay-hr-policy.pdf"

init_db()

app = FastAPI(
    title="Document Q&A API (RAG)",
    description=(
        "Upload a PDF or text file, then ask questions about it in plain English. Answers are drawn only "
        "from your document and cite the passages they came from; if the document doesn't contain the "
        "answer, the API says so.\n\nSign up, log in, then click **Authorize** to call the document routes. "
        "Prefer clicking to coding? The web app is at [/](/)."
    ),
    version="1.1.0",
)
app.include_router(auth.router)
app.include_router(documents.router)


@app.get("/", include_in_schema=False)
def web_app():
    """The friendly web interface: upload a document and ask questions without writing code."""
    return FileResponse(WEB_PAGE, media_type="text/html")


@app.get("/sample-document", tags=["system"], response_class=FileResponse)
def sample_document():
    """The fictional HR policy PDF used by the web app's 'Try the sample' button."""
    return FileResponse(SAMPLE_PDF, media_type="application/pdf", filename=SAMPLE_PDF.name)


@app.get("/health", tags=["system"])
def health(embedder=Depends(get_embedder), answerer=Depends(get_answerer)):
    """Liveness check that also reports which providers are active (never any keys)."""
    return {"status": "ok", "embeddings": embedder.name, "answerer": answerer.name}
