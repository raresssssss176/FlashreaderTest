"""
client/ui/widgets/virtual_controls.py

On-screen stand-ins for the physical controls, pinned to the bottom of
every screen. Lets you exercise the exact same code paths the GPIO will
drive later:

    SELECT   -> short press  (activates whatever has focus)
    HOLD     -> long press   (back / home)
    -/+ WPM  -> potentiometer

Hide it from Settings once the real hardware is wired up.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class VirtualControls(QWidget):
    def __init__(self, bus, parent=None):
        super().__init__(parent)
        self.bus = bus

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        tag = QLabel("HW", self)
        tag.setObjectName("hint")
        layout.addWidget(tag)

        self.btn_select = QPushButton("\u25CF  SELECT", self)
        self.btn_select.setObjectName("ghost")
        # press/release rather than clicked, so the hold timer works exactly
        # like the real button.
        self.btn_select.pressed.connect(self.bus.press_started)
        self.btn_select.released.connect(self.bus.press_released)
        self.btn_select.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.btn_select)

        self.btn_hold = QPushButton("\u21BA  HOLD (back)", self)
        self.btn_hold.setObjectName("ghost")
        self.btn_hold.clicked.connect(self.bus.back.emit)
        self.btn_hold.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.btn_hold)

        layout.addStretch(1)

        self.btn_minus = QPushButton("\u2212 WPM", self)
        self.btn_minus.setObjectName("ghost")
        self.btn_minus.clicked.connect(lambda: self.bus.wpm_delta.emit(-10))
        self.btn_minus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.btn_minus)

        self.btn_plus = QPushButton("+ WPM", self)
        self.btn_plus.setObjectName("ghost")
        self.btn_plus.clicked.connect(lambda: self.bus.wpm_delta.emit(10))
        self.btn_plus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.btn_plus)
