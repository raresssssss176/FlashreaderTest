"""
client/ui/screens/settings_screen.py
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QCheckBox
from PyQt6.QtCore import Qt
from client.db.database import LocalDatabase


class SettingsScreen(QWidget):
    def __init__(self, router):
        super().__init__()
        self.router = router
        self.db = LocalDatabase()

        layout = QVBoxLayout(self)

        title = QLabel("SETĂRI", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(title)

        # Night mode toggle
        self.night_mode_cb = QCheckBox("Night Mode 🌙", self)
        self.night_mode_cb.setStyleSheet("font-size: 18px; color: #FFFFFF; padding: 10px;")
        current_night = self.db.get_setting("night_mode", "false") == "true"
        self.night_mode_cb.setChecked(current_night)
        self.night_mode_cb.toggled.connect(self._toggle_night_mode)
        layout.addWidget(self.night_mode_cb)

        # Settings options list matching paper sketch
        btn_font = QPushButton("FONT", self)
        btn_colors = QPushButton("CULORI", self)
        btn_anim = QPushButton("ANIMAȚII", self)
        btn_bright = QPushButton("LUMINOZITATE", self)

        for btn in (btn_font, btn_colors, btn_anim, btn_bright):
            btn.setStyleSheet("background-color: #262626; color: #FFFFFF; font-size: 18px; padding: 10px; border-radius: 6px;")
            layout.addWidget(btn)

        # Back button
        btn_back = QPushButton("ÎNAPOI", self)
        btn_back.setStyleSheet("background-color: #D32F2F; color: #FFFFFF; font-size: 16px; padding: 10px; margin-top: 10px;")
        btn_back.clicked.connect(lambda: self.router.navigate_to(0))
        layout.addWidget(btn_back)

    def _toggle_night_mode(self, checked: bool):
        val = "true" if checked else "false"
        self.db.update_setting("night_mode", val)