"""
server/routes/store.py

Catalog + ingestion. A book enters here as raw text, a .txt or a .pdf,
gets analyzed once, and is stored with its instruction payload so the
device only ever downloads a finished array of {w, i, p}.
"""

import json
import re
import uuid
from typing import List, Optional

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query,
                     UploadFile)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.database import get_db
from server.models import Book, BookInstruction
from server.pipeline.analyzer import BookAnalyzerPipeline, nlp_status
from server.pipeline.extract import ExtractionError, extract, clean_text

router = APIRouter(prefix="/store", tags=["Store"])
analyzer = BookAnalyzerPipeline()

MAX_UPLOAD_BYTES = 40 * 1024 * 1024  # 40 MB


class BookCreateRequest(BaseModel):
    title: str
    author: str
    raw_text: str
    id: Optional[str] = None
    price: float = 0.0
    use_llm: bool = False


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:40] or uuid.uuid4().hex[:8]


def _ingest(db: Session, *, book_id: str, title: str, author: str,
            price: float, text: str, source: str, use_llm: bool) -> dict:
    """Analyze once, then upsert the book and its payload."""
    text = clean_text(text)
    if len(text.split()) < 20:
        raise HTTPException(status_code=400,
                            detail="Textul este prea scurt pentru analiza.")

    result = analyzer.analyze(text, use_llm=use_llm)
    tokens = result["tokens"]
    stats = result["stats"]

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        book = Book(id=book_id)
        db.add(book)

    book.title = title
    book.author = author
    book.price = price
    book.word_count = len(tokens)
    book.source = source
    book.analyzed_with_llm = bool(stats["llm"].get("used"))
    book.avg_penalty = stats["avg_penalty"]
    book.nlp_engine = stats["nlp"][:80]

    payload = db.query(BookInstruction).filter(
        BookInstruction.book_id == book_id).first()
    if not payload:
        payload = BookInstruction(book_id=book_id)
        db.add(payload)
    payload.instructions_json = json.dumps(tokens, ensure_ascii=False)
    payload.raw_text = text

    db.commit()

    return {"status": "success", "book_id": book_id, "title": title,
            "tokens": len(tokens), "stats": {k: v for k, v in stats.items()
                                             if k != "config"}}


# ------------------------------------------------------------------ catalog

@router.get("/catalog")
def get_catalog(db: Session = Depends(get_db)):
    books = db.query(Book).order_by(Book.created_at.desc()).all()
    return [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "price": b.price,
            "word_count": b.word_count or 0,
            "source": b.source,
            "analyzed_with_llm": bool(b.analyzed_with_llm),
            "avg_penalty": b.avg_penalty or 0.0,
        }
        for b in books
    ]


@router.get("/health")
def health():
    return {"nlp": nlp_status(), "llm_model": analyzer.model,
            "llm_key_present": bool(analyzer.api_key)}


# ---------------------------------------------------------------- ingestion

@router.post("/upload")
def upload_book_json(req: BookCreateRequest, db: Session = Depends(get_db)):
    """Paste raw text straight in (handy for quick tests and scripts)."""
    book_id = req.id or slugify(req.title)
    return _ingest(db, book_id=book_id, title=req.title, author=req.author,
                   price=req.price, text=req.raw_text, source="text",
                   use_llm=req.use_llm)


@router.post("/upload/file")
async def upload_book_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form("Necunoscut"),
    price: float = Form(0.0),
    book_id: Optional[str] = Form(None),
    use_llm: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Upload a .pdf, .txt or .md and run the full pipeline on it."""
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Fisier prea mare (max 40 MB).")

    try:
        text, source = extract(file.filename, data)
    except ExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _ingest(db, book_id=book_id or slugify(title), title=title,
                   author=author, price=price, text=text, source=source,
                   use_llm=use_llm)


@router.post("/books/{book_id}/reanalyze")
def reanalyze(book_id: str, use_llm: bool = Query(False),
              db: Session = Depends(get_db)):
    """Re-run the pipeline on stored text after tuning the penalties."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book or not book.payload or not book.payload.raw_text:
        raise HTTPException(status_code=404,
                            detail="Textul original nu a fost pastrat pentru aceasta carte.")
    return _ingest(db, book_id=book.id, title=book.title, author=book.author,
                   price=book.price, text=book.payload.raw_text,
                   source=book.source or "text", use_llm=use_llm)


@router.delete("/books/{book_id}")
def delete_book(book_id: str, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Cartea nu exista.")
    db.delete(book)
    db.commit()
    return {"status": "deleted", "book_id": book_id}


# ----------------------------------------------------------------- delivery

@router.get("/download/{book_id}")
def download_book_payload(book_id: str, db: Session = Depends(get_db)):
    """Everything the device needs: metadata plus the instruction array."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book or not book.payload:
        raise HTTPException(status_code=404,
                            detail="Cartea sau instructiunile nu exista.")
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "word_count": book.word_count or 0,
        "payload": json.loads(book.payload.instructions_json),
    }


@router.get("/books/{book_id}/preview")
def preview_book(book_id: str, limit: int = Query(60, ge=1, le=500),
                 db: Session = Depends(get_db)):
    """First N tokens with their penalties, for checking the analysis."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book or not book.payload:
        raise HTTPException(status_code=404, detail="Cartea nu exista.")
    tokens: List[dict] = json.loads(book.payload.instructions_json)
    return {"id": book.id, "title": book.title, "total": len(tokens),
            "tokens": tokens[:limit]}
