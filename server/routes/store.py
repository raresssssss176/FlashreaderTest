"""
server/routes/store.py
"""

import json
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from server.models import Book, BookInstruction
from server.database import get_db
from server.pipeline.analyzer import BookAnalyzerPipeline

router = APIRouter(prefix="/store", tags=["Store"])
analyzer = BookAnalyzerPipeline()


class BookCreateRequest(BaseModel):
    id: str
    title: str
    author: str
    price: float
    raw_text: str  # Plain text of the book to process through NLP


@router.get("/catalog")
def get_catalog(db: Session = Depends(get_db)):
    """Fetch available books in store."""
    books = db.query(Book).all()
    return [{"id": b.id, "title": b.title, "author": b.author, "price": b.price} for b in books]


@router.post("/upload")
def upload_and_process_book(req: BookCreateRequest, db: Session = Depends(get_db)):
    """Uploads a book, runs NLP pipeline, and generates instructions JSON payload."""
    tokens = analyzer.process_text(req.raw_text)
    instructions_str = json.dumps(tokens)

    book = Book(id=req.id, title=req.title, author=req.author, price=req.price)
    instruction_record = BookInstruction(book_id=req.id, instructions_json=instructions_str)

    db.add(book)
    db.add(instruction_record)
    db.commit()

    return {"status": "success", "book_id": req.id, "processed_tokens": len(tokens)}


@router.get("/download/{book_id}")
def download_book_payload(book_id: str, db: Session = Depends(get_db)):
    """Delivers title, metadata, and calculated token instructions to the Pi."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book or not book.payload:
        raise HTTPException(status_code=404, detail="Book or instructions not found")

    tokens = json.loads(book.payload.instructions_json)
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "payload": tokens
    }