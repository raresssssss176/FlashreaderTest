"""
client/ui/screens/library_screen.py
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QScrollArea, QFrame
from PyQt6.QtCore import Qt
from client.db.database import LocalDatabase


class LibraryScreen(QWidget):
    def __init__(self, router):
        super().__init__()
        self.router = router
        self.db = LocalDatabase()

        self.layout = QVBoxLayout(self)

        header = QLabel("LIBRĂRIE / CĂRȚILE TALE", self)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #FFFFFF;")
        self.layout.addWidget(header)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)

        self.refresh_library()

    def refresh_library(self):
        # Clear existing items
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        books = self.db.get_library_books()
        if not books:
            empty_lbl = QLabel("Nicio carte descărcată.", self)
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.scroll_layout.addWidget(empty_lbl)
            return

        for book in books:
            btn_text = f"{book['title']}\n{book['author']} — {book['progress_percentage']}%"
            btn = QPushButton(btn_text, self)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E1E1E;
                    color: #FFFFFF;
                    font-size: 18px;
                    text-align: left;
                    padding: 15px;
                    border-radius: 6px;
                    border: 1px solid #333333;
                }
                QPushButton:pressed {
                    background-color: #333333;
                }
            """)
            book_id = book['id']
            btn.clicked.connect(lambda checked, b_id=book_id: self._open_book(b_id))
            self.scroll_layout.addWidget(btn)

    def _open_book(self, book_id: str):
        book_meta, tokens = self.db.get_book_payload(book_id)
        if book_meta and tokens:
            self.router.reader_screen.load_book(book_meta, tokens)
            self.router.navigate_to(4)