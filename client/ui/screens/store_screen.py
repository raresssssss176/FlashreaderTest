"""
client/ui/screens/store_screen.py

Talks to the FastAPI server: lists the catalog and downloads a book plus
its instruction payload into the local SQLite database.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QScrollArea,
                             QVBoxLayout, QWidget)

from client.core.api_client import ApiClient, NetworkTask
from client.ui.screens.base_screen import BaseScreen


class StoreScreen(BaseScreen):
    title = "MAGAZIN"

    def __init__(self, router):
        super().__init__(router)
        self.db = router.db
        self.api = ApiClient(self.db.get_setting("server_url", "http://127.0.0.1:8000"))
        self._tasks = []  # keep references so threads are not garbage collected

        self.status = QLabel("", self)
        self.status.setObjectName("hint")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(self.status)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        self.body.addWidget(self.scroll)

        btn_refresh = QPushButton("\u21BB", self)
        btn_refresh.setObjectName("ghost")
        btn_refresh.clicked.connect(self.refresh_catalog)
        self.nav_bar.add_action(btn_refresh)

    def on_enter(self) -> None:
        self.api.set_base_url(self.db.get_setting("server_url", "http://127.0.0.1:8000"))
        self.refresh_catalog()

    # ------------------------------------------------------------------ data
    def refresh_catalog(self) -> None:
        self.status.setText("Se incarca...")
        self._run(self.api.get_catalog, self._render_catalog)

    def _run(self, fn, on_ok) -> None:
        task = NetworkTask(fn, self)
        task.finished_ok.connect(on_ok)
        task.finished_err.connect(self._on_error)
        task.finished.connect(lambda t=task: self._tasks.remove(t) if t in self._tasks else None)
        self._tasks.append(task)
        task.start()

    def _on_error(self, message: str) -> None:
        self.status.setText(message)

    # -------------------------------------------------------------------- ui
    def _render_catalog(self, books) -> None:
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not books:
            self.status.setText("Catalogul este gol. Incarca o carte din /admin pe server.")
            return

        owned = {b["id"] for b in self.db.get_library_books()}
        self.status.setText(f"{len(books)} carti disponibile")

        for book in books:
            self.scroll_layout.addWidget(self._make_row(book, book["id"] in owned))

    def _make_row(self, book: dict, owned: bool) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        words = book.get("word_count") or 0
        info = QLabel(f"{book['title']}\n{book['author']}  -  {words} cuvinte", row)
        info.setStyleSheet("padding: 10px;")
        layout.addWidget(info, 1)

        action = QPushButton("DESCARCAT" if owned else "DESCARCA", row)
        if not owned:
            action.setObjectName("primary")
        action.setEnabled(not owned)
        action.setFixedWidth(150)
        action.clicked.connect(lambda _, b=book, btn=action: self._download(b, btn))
        layout.addWidget(action)

        return row

    def _download(self, book: dict, button: QPushButton) -> None:
        button.setEnabled(False)
        button.setText("...")
        book_id = book["id"]

        def on_ok(payload):
            tokens = payload.get("payload") or []
            if not tokens:
                self.status.setText("Cartea nu are instructiuni generate.")
                button.setEnabled(True)
                button.setText("DESCARCA")
                return
            self.db.save_book(payload["id"], payload["title"],
                              payload["author"], tokens)
            button.setText("DESCARCAT")
            self.status.setText(f"\"{payload['title']}\" salvata local ({len(tokens)} cuvinte).")

        self._run(lambda: self.api.download_book(book_id), on_ok)
