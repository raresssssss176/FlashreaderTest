"""
server/models.py
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, Float
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

    payload = relationship("BookInstruction", uselist=False, back_populates="book")


class BookInstruction(Base):
    __tablename__ = "book_instructions"

    book_id = Column(String(50), ForeignKey("books.id"), primary_key=True)
    instructions_json = Column(Text, nullable=False)  # Stored JSON array of [{w, i}]

    book = relationship("Book", back_populates="payload")