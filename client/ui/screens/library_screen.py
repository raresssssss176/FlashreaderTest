"""
client/ui/screens/library_screen.py
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QProgressBar,
                             QPushButton, QScrollArea, QVBoxLayout, QWidget)

from client.ui.screens.base_screen import BaseScreen


class LibraryScreen(BaseScreen):
    title = "LIBRARIE"

    def __init__(self, router):
        super().__init__(router)
        self.db = router.db

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        self.body.addWidget(self.scroll)

        btn_store = QPushButton("+ MAGAZIN", self)
        btn_store.setObjectName("ghost")
        btn_store.clicked.connect(lambda: self.router.navigate_to(2))
        self.nav_bar.add_action(btn_store)

    def on_enter(self) -> None:
        self.refresh_library()

    def refresh_library(self) -> None:
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        books = self.db.get_library_books()
        if not books:
            empty = QLabel("Nicio carte descarcata.\nDeschide MAGAZIN pentru a adauga.", self)
            empty.setObjectName("hint")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.scroll_layout.addWidget(empty)
            return

        for book in books:
            self.scroll_layout.addWidget(self._make_row(book))

    def _make_row(self, book: dict) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        open_btn = QPushButton(row)
        open_btn.setText(f"{book['title']}\n{book['author']}")
        open_btn.setStyleSheet("text-align: left;")
        open_btn.clicked.connect(lambda _, bid=book["id"]: self._open(bid))
        layout.addWidget(open_btn, 1)

        meta = QWidget(row)
        meta_layout = QVBoxLayout(meta)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        pct = QLabel(f"{book['progress_percentage']:.0f}%", meta)
        pct.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar = QProgressBar(meta)
        bar.setRange(0, 100)
        bar.setValue(int(book["progress_percentage"]))
        bar.setTextVisible(False)
        meta_layout.addWidget(pct)
        meta_layout.addWidget(bar)
        meta.setFixedWidth(90)
        layout.addWidget(meta)

        del_btn = QPushButton("\u2715", row)
        del_btn.setObjectName("danger")
        del_btn.setFixedWidth(54)
        del_btn.clicked.connect(lambda _, b=book: self._delete(b))
        layout.addWidget(del_btn)

        return row

    def _open(self, book_id: str) -> None:
        if not self.router.open_book(book_id):
            QMessageBox.warning(self, "Eroare",
                                "Cartea nu are instructiuni salvate local. "
                                "Descarc-o din nou din magazin.")

    def _delete(self, book: dict) -> None:
        confirm = QMessageBox.question(
            self, "Sterge", f"Stergi \"{book['title']}\" de pe dispozitiv?")
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_book(book["id"])
            self.refresh_library()
