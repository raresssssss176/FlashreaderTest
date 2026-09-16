"""
client/db/models.py

SQL statements for creating local database tables.
"""

CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CREATE_BOOKS_TABLE = """
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    total_words INTEGER NOT NULL,
    current_word_index INTEGER DEFAULT 0,
    progress_percentage REAL DEFAULT 0.0,
    last_read_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_BOOK_PAYLOADS_TABLE = """
CREATE TABLE IF NOT EXISTS book_payloads (
    book_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
);
"""