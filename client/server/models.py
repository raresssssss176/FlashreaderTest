"""
server/models.py
"""

from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Device(Base):
    __tablename__ = "devices"

    device_code = Column(String(50), primary_key=True, index=True)
    owner_name = Column(String(100), nullable=True)


class Book(Base):
    __tablename__ = "books"

    id = Column(String(50), primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    author = Column(String(100), nullable=False)
    price = Column(Float, default=0.0)

    # Populated by the analysis pipeline
    word_count = Column(Integer, default=0)
    source = Column(String(20), default="text")       # pdf | txt | text
    analyzed_with_llm = Column(Boolean, default=False)
    avg_penalty = Column(Float, default=0.0)
    nlp_engine = Column(String(80), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    payload = relationship("BookInstruction", uselist=False,
                           back_populates="book",
                           cascade="all, delete-orphan")


class BookInstruction(Base):
    __tablename__ = "book_instructions"

    book_id = Column(String(50), ForeignKey("books.id"), primary_key=True)
    instructions_json = Column(Text, nullable=False)  # JSON array of {w,i,p}
    raw_text = Column(Text, nullable=True)            # kept so we can re-analyze

    book = relationship("Book", back_populates="payload")
