"""
client/ui/widgets/nav_bar.py

Touch-friendly header with a real on-screen BACK button, so the whole
device is testable without the physical hold-button.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class NavBar(QWidget):
    def __init__(self, title: str, on_back, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(10)

        self.btn_back = QPushButton("\u2039  INAPOI", self)
        self.btn_back.setObjectName("ghost")
        self.btn_back.setFixedWidth(130)
        self.btn_back.clicked.connect(on_back)
        layout.addWidget(self.btn_back)

        self.title = QLabel(title, self)
        self.title.setObjectName("screenTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title, 1)

        # Keeps the title optically centred; screens can drop a button here.
        self.slot = QWidget(self)
        self.slot_layout = QHBoxLayout(self.slot)
        self.slot_layout.setContentsMargins(0, 0, 0, 0)
        self.slot.setFixedWidth(130)
        layout.addWidget(self.slot)

    def set_title(self, text: str) -> None:
        self.title.setText(text)

    def add_action(self, button: QPushButton) -> None:
        self.slot_layout.addWidget(button)
