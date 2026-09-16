"""
client/db/database.py

Database helper for local SQLite storage on the Raspberry Pi.
Handles user settings, book metadata, reading progress, and word instructions.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from client.db.models import (
    CREATE_SETTINGS_TABLE,
    CREATE_BOOKS_TABLE,
    CREATE_BOOK_PAYLOADS_TABLE
)

# Store the DB file in the user's home directory or local client folder
DB_PATH = Path(__file__).parent.parent / "flashreader_local.db"


class LocalDatabase:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        """Initializes tables and populates default settings if missing."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(CREATE_SETTINGS_TABLE)
            cursor.execute(CREATE_BOOKS_TABLE)
            cursor.execute(CREATE_BOOK_PAYLOADS_TABLE)
            conn.commit()

        # Seed default settings if not present
        self._seed_default_settings()

    def _seed_default_settings(self):
        defaults = {
            "base_wpm": "300",
            "font_family": "Arial",
            "font_size": "48",
            "night_mode": "false",
            "text_color": "#FFFFFF",
            "bg_color": "#121212",
            "eye_tracking_enabled": "true"
        }
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for key, val in defaults.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, val)
                )
            conn.commit()

    # -------------------------------------------------------------------------
    # SETTINGS HELPERS
    # -------------------------------------------------------------------------
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Fetch a specific setting value by key."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def get_all_settings(self) -> Dict[str, str]:
        """Fetch all key-value settings into a dictionary."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            rows = cursor.fetchall()
            return {row["key"]: row["value"] for row in rows}

    def update_setting(self, key: str, value: str):
        """Update or insert a setting value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value))
            )
            conn.commit()

    # -------------------------------------------------------------------------
    # BOOK METADATA & PROGRESS HELPERS
    # -------------------------------------------------------------------------
    def save_book(self, book_id: str, title: str, author: str, payload: List[Dict[str, Any]]):
        """
        Saves a newly acquired book, its total word count, and its word payload.
        payload format: [{"w": "Word", "i": 20}, ...]
        """
        total_words = len(payload)
        payload_json_str = json.dumps(payload)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Insert or update metadata
            cursor.execute(
                """
                INSERT INTO books (id, title, author, total_words)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    author = excluded.author,
                    total_words = excluded.total_words
                """,
                (book_id, title, author, total_words)
            )

            # 2. Insert or update payload JSON
            cursor.execute(
                """
                INSERT INTO book_payloads (book_id, payload_json)
                VALUES (?, ?)
                ON CONFLICT(book_id) DO UPDATE SET
                    payload_json = excluded.payload_json
                """,
                (book_id, payload_json_str)
            )
            conn.commit()

    def update_progress(self, book_id: str, current_word_index: int):
        """Updates the reading progress for a given book."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # First get total words to calculate percentage
            cursor.execute("SELECT total_words FROM books WHERE id = ?", (book_id,))
            row = cursor.fetchone()
            if not row:
                return

            total_words = row["total_words"]
            percentage = (current_word_index / total_words * 100.0) if total_words > 0 else 0.0
            percentage = min(100.0, max(0.0, percentage))

            cursor.execute(
                """
                UPDATE books
                SET current_word_index = ?,
                    progress_percentage = ?,
                    last_read_timestamp = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (current_word_index, round(percentage, 2), book_id)
            )
            conn.commit()

    def get_library_books(self) -> List[Dict[str, Any]]:
        """Fetch all books ordered by recently read."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, title, author, total_words, current_word_index, 
                       progress_percentage, last_read_timestamp 
                FROM books 
                ORDER BY last_read_timestamp DESC
                """
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_book_payload(self, book_id: str) -> Optional[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
        """
        Retrieves book details and its full word token/instruction payload.
        Returns: (book_metadata_dict, tokens_list)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            book_row = cursor.fetchone()

            if not book_row:
                return None

            cursor.execute("SELECT payload_json FROM book_payloads WHERE book_id = ?", (book_id,))
            payload_row = cursor.fetchone()

            if not payload_row:
                return None

            tokens = json.loads(payload_row["payload_json"])
            return dict(book_row), tokens

    def delete_book(self, book_id: str):
        """Removes a book and its payload from local storage."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()