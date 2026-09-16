"""
client/ui/screens/home_screen.py
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt


class HomeScreen(QWidget):
    def __init__(self, router):
        super().__init__()
        self.router = router
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("FLASHREADER", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #00E676; margin-bottom: 10px;")
        layout.addWidget(title)

        btn_continue = QPushButton("CONTINUĂ", self)
        btn_library = QPushButton("LIBRĂRIE", self)
        btn_store = QPushButton("MAGAZIN", self)
        btn_settings = QPushButton("SETĂRI", self)

        for btn in (btn_continue, btn_library, btn_store, btn_settings):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #262626;
                    color: #FFFFFF;
                    font-size: 20px;
                    border-radius: 8px;
                    padding: 12px;
                }
                QPushButton:pressed {
                    background-color: #00E676;
                    color: #000000;
                }
            """)
            layout.addWidget(btn)

        btn_continue.clicked.connect(lambda: self.router.navigate_to(1))
        btn_library.clicked.connect(lambda: self.router.navigate_to(1))
        btn_store.clicked.connect(lambda: self.router.navigate_to(2))
        btn_settings.clicked.connect(lambda: self.router.navigate_to(3))