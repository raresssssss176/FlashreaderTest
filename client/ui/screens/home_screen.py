"""
client/ui/screens/home_screen.py
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QPushButton

from client.ui.screens.base_screen import BaseScreen


class HomeScreen(BaseScreen):
    show_nav_bar = False

    def __init__(self, router):
        super().__init__(router)
        self.db = router.db

        title = QLabel("FLASHREADER", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 34px; font-weight: bold; letter-spacing: 3px;")
        self.body.addWidget(title)

        self.subtitle = QLabel("", self)
        self.subtitle.setObjectName("hint")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(self.subtitle)

        self.body.addSpacing(10)

        self.btn_continue = QPushButton("CONTINUA", self)
        self.btn_continue.setObjectName("primary")
        self.btn_continue.clicked.connect(self._continue_reading)

        self.btn_library = QPushButton("LIBRARIE", self)
        self.btn_library.clicked.connect(lambda: self.router.navigate_to(1))

        self.btn_store = QPushButton("MAGAZIN", self)
        self.btn_store.clicked.connect(lambda: self.router.navigate_to(2))

        self.btn_settings = QPushButton("SETARI", self)
        self.btn_settings.clicked.connect(lambda: self.router.navigate_to(3))

        for btn in (self.btn_continue, self.btn_library,
                    self.btn_store, self.btn_settings):
            self.body.addWidget(btn)

        self.body.addStretch(1)

        self.status = QLabel("", self)
        self.status.setObjectName("hint")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(self.status)

    def on_enter(self) -> None:
        book = self.db.get_last_read_book()
        if book:
            self.btn_continue.setEnabled(True)
            self.btn_continue.setText(f"CONTINUA\n{book['title']}  ({book['progress_percentage']:.0f}%)")
            self.subtitle.setText("Apasa SELECT pentru a relua lectura")
        else:
            self.btn_continue.setEnabled(False)
            self.btn_continue.setText("CONTINUA")
            self.subtitle.setText("Nicio carte inceputa - descarca una din MAGAZIN")

        wpm = self.db.get_setting("base_wpm", "300")
        count = len(self.db.get_library_books())
        self.status.setText(f"{count} carti in librarie  -  {wpm} WPM")

    def _continue_reading(self) -> None:
        book = self.db.get_last_read_book()
        if book:
            self.router.open_book(book["id"])
