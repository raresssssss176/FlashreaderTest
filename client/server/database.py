"""
server/database.py
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./server_flashreader.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# SQL types for columns added after the first release. create_all() only
# creates missing *tables*, never missing columns, so an existing
# server_flashreader.db would break without this.
_ADDED_COLUMNS = {
    "books": {
        "word_count": "INTEGER DEFAULT 0",
        "source": "VARCHAR(20) DEFAULT 'text'",
        "analyzed_with_llm": "BOOLEAN DEFAULT 0",
        "avg_penalty": "FLOAT DEFAULT 0",
        "nlp_engine": "VARCHAR(80) DEFAULT ''",
        "created_at": "DATETIME",
    },
    "book_instructions": {
        "raw_text": "TEXT",
    },
}


def ensure_schema() -> None:
    """Adds any column introduced since the database file was created."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            if table not in existing_tables:
                continue
            present = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
