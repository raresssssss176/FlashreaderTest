"""
client/ui/screens/reader_screen.py
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from client.db.database import LocalDatabase


class ReaderScreen(QWidget):
    def __init__(self, router):
        super().__init__()
        self.router = router
        self.db = LocalDatabase()

        layout = QVBoxLayout(self)

        self.word_label = QLabel("...", self)
        self.word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_label.setStyleSheet("font-size: 52px; font-weight: bold; color: #00E676;")
        layout.addWidget(self.word_label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_word)

        self.tokens = []
        self.book_meta = None
        self.current_idx = 0
        self.base_wpm = int(self.db.get_setting("base_wpm", "300"))
        self.eye_penalty = 0

    def load_book(self, book_meta: dict, tokens: list):
        self.book_meta = book_meta
        self.tokens = tokens
        self.current_idx = book_meta.get("current_word_index", 0)
        self.start_reading()

    def set_hardware_wpm(self, wpm: int):
        self.base_wpm = wpm

    def set_eye_penalty(self, penalty: int):
        self.eye_penalty = penalty

    def start_reading(self):
        if self.tokens:
            self._render_word()

    def _render_word(self):
        if self.current_idx >= len(self.tokens):
            self.word_label.setText("SFÂRȘIT")
            return

        token = self.tokens[self.current_idx]
        word = token["w"]
        instruction_penalty = token.get("i", 0)

        # Formula: Effective WPM = UserSetWPM - InstructionPenalty - EyePenalty
        effective_wpm = max(60, self.base_wpm - instruction_penalty - self.eye_penalty)
        delay_ms = int((60.0 / effective_wpm) * 1000)

        self.word_label.setText(word)
        self.current_idx += 1

        # Periodically save progress to SQLite every 20 words
        if self.current_idx % 20 == 0 and self.book_meta:
            self.db.update_progress(self.book_meta["id"], self.current_idx)

        self.timer.start(delay_ms)

    def _next_word(self):
        self.timer.stop()
        self._render_word()