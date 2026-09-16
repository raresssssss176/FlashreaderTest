"""
client/ui/screens/reader_screen.py

One word at a time (RSVP). Speed for each word comes from:

    effective_wpm = base_wpm - book_instruction - eye_penalty

base_wpm      mouse wheel here, potentiometer on the device
instruction   precomputed on the server by the NLP/LLM pipeline
eye_penalty   stays 0 until the camera is enabled
"""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QFont, QPainter, QPen
from PyQt6.QtWidgets import (QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                             QProgressBar, QPushButton, QVBoxLayout, QWidget)

from client.core.wpm_controller import WpmController
from client.ui.screens.base_screen import BaseScreen
from client.ui.theme import palette


def pivot_index(word: str) -> int:
    """Optimal recognition point - where the eye naturally lands."""
    length = len(word)
    if length <= 1:
        return 0
    if length <= 5:
        return 1
    if length <= 9:
        return 2
    if length <= 13:
        return 3
    return 4


class WordDisplay(QWidget):
    """
    Three labels side by side so the focus letter stays nailed to the
    centre of the screen no matter how long the word is. The eye then
    never has to travel between words.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_pivot = True
        self.pivot_color = "#FF3D57"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.left = QLabel("", self)
        self.left.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.pivot = QLabel("", self)
        self.pivot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right = QLabel("", self)
        self.right.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self.left, 1)
        layout.addWidget(self.pivot, 0)
        layout.addWidget(self.right, 1)

        self.set_font_size(56)

    def set_font_size(self, size: int) -> None:
        font = QFont()
        font.setPointSize(int(size / 1.6))
        font.setBold(True)
        for label in (self.left, self.pivot, self.right):
            label.setFont(font)
        # Fixed width keeps the pivot column from jittering between letters
        self.pivot.setFixedWidth(self.fontMetrics().horizontalAdvance("W") * 2)

    def set_word(self, word: str) -> None:
        idx = pivot_index(word)
        self.left.setText(word[:idx])
        self.right.setText(word[idx + 1:])
        letter = word[idx] if word else ""
        if self.show_pivot:
            self.pivot.setText(
                f'<span style="color:{self.pivot_color}">{letter}</span>')
        else:
            self.pivot.setText(letter)

    def paintEvent(self, event):
        """Two small guide ticks marking the focus column."""
        super().paintEvent(event)
        if not self.show_pivot:
            return
        painter = QPainter(self)
        pen = QPen()
        pen.setWidth(2)
        pen.setColor(self.palette().mid().color())
        painter.setPen(pen)
        x = self.width() // 2
        painter.drawLine(x, 0, x, 14)
        painter.drawLine(x, self.height() - 14, x, self.height())
        painter.end()


class ReaderScreen(BaseScreen):
    title = "LECTURA"

    def __init__(self, router):
        super().__init__(router)
        self.db = router.db

        self.wpm = WpmController(
            base_wpm=int(self.db.get_setting("base_wpm", "300")))
        self.wpm.instruction_gain = float(
            self.db.get_setting("instruction_gain", "1.0"))

        self.tokens = []
        self.book_meta = None
        self.current_idx = 0
        self.paused = True
        self.animations_on = True

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._advance)

        # ---- HUD -----------------------------------------------------------
        self.hud = QLabel("", self)
        self.hud.setObjectName("hint")
        self.hud.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(self.hud)

        # ---- word ----------------------------------------------------------
        self.display = WordDisplay(self)
        self.body.addWidget(self.display, 1)

        self.opacity = QGraphicsOpacityEffect(self.display)
        self.opacity.setOpacity(1.0)
        self.display.setGraphicsEffect(self.opacity)
        self.fade = QPropertyAnimation(self.opacity, b"opacity", self)
        self.fade.setDuration(90)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        # ---- progress ------------------------------------------------------
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.body.addWidget(self.progress)

        self.position = QLabel("", self)
        self.position.setObjectName("hint")
        self.position.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(self.position)

        # ---- transport controls -------------------------------------------
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.btn_back10 = QPushButton("\u23EA  10", self)
        self.btn_back10.setObjectName("ghost")
        self.btn_back10.clicked.connect(lambda: self.skip(-10))
        controls.addWidget(self.btn_back10)

        self.btn_play = QPushButton("\u25B6  START", self)
        self.btn_play.setObjectName("primary")
        self.btn_play.clicked.connect(self.toggle_pause)
        controls.addWidget(self.btn_play, 2)

        self.btn_fwd10 = QPushButton("10  \u23E9", self)
        self.btn_fwd10.setObjectName("ghost")
        self.btn_fwd10.clicked.connect(lambda: self.skip(10))
        controls.addWidget(self.btn_fwd10)

        self.body.addLayout(controls)

        wheel_hint = QLabel("Rotita mouse-ului = WPM  |  SELECT = pauza  |  HOLD = inapoi", self)
        wheel_hint.setObjectName("hint")
        wheel_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(wheel_hint)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ------------------------------------------------------------ book state
    def load_book(self, book_meta: dict, tokens: list) -> None:
        self.book_meta = book_meta
        self.tokens = tokens
        self.current_idx = int(book_meta.get("current_word_index", 0) or 0)
        if self.current_idx >= len(tokens):
            self.current_idx = 0
        self.paused = True
        self._apply_settings()
        if self.nav_bar:
            self.nav_bar.set_title(book_meta.get("title", "LECTURA"))
        self._render_current()
        self._update_hud()

    def _apply_settings(self) -> None:
        self.display.set_font_size(int(self.db.get_setting("font_size", "56")))
        self.display.show_pivot = self.db.get_setting("focus_letter", "true") == "true"
        self.display.pivot_color = palette(
            self.db.get_setting("night_mode", "false") == "true")["pivot"]
        self.hud.setVisible(self.db.get_setting("show_hud", "true") == "true")
        self.animations_on = self.db.get_setting("animations", "true") == "true"
        self.wpm.set_base(int(self.db.get_setting("base_wpm", "300")))
        self.wpm.instruction_gain = float(
            self.db.get_setting("instruction_gain", "1.0"))

    def on_enter(self) -> None:
        self._apply_settings()
        self.setFocus()
        self._update_hud()

    def on_leave(self) -> None:
        self.pause()
        self._save_progress()

    # ---------------------------------------------------------------- engine
    def toggle_pause(self) -> None:
        self.pause() if not self.paused else self.play()

    def play(self) -> None:
        if not self.tokens or self.current_idx >= len(self.tokens):
            return
        self.paused = False
        self.btn_play.setText("\u23F8  PAUZA")
        self._schedule_next()

    def pause(self) -> None:
        self.paused = True
        self.timer.stop()
        self.btn_play.setText("\u25B6  START")

    def skip(self, amount: int) -> None:
        if not self.tokens:
            return
        self.current_idx = max(0, min(len(self.tokens) - 1, self.current_idx + amount))
        self._render_current()
        self._update_hud()

    def _schedule_next(self) -> None:
        if self.paused or self.current_idx >= len(self.tokens):
            return
        delay = self.wpm.delay_ms(self.tokens[self.current_idx])
        self.timer.start(delay)

    def _advance(self) -> None:
        self.current_idx += 1
        if self.current_idx >= len(self.tokens):
            self._finish()
            return
        self._render_current()
        if self.current_idx % 20 == 0:
            self._save_progress()
        self._schedule_next()

    def _render_current(self) -> None:
        if not self.tokens:
            self.display.set_word("...")
            return
        token = self.tokens[self.current_idx]
        self.display.set_word(token.get("w", ""))

        # Fade only when there is time for it; above ~330 WPM it is a blur.
        if self.animations_on and self.wpm.last_effective_wpm < 330:
            self.fade.stop()
            self.fade.setStartValue(0.35)
            self.fade.setEndValue(1.0)
            self.fade.start()

        self._update_progress()
        self._update_hud()

    def _finish(self) -> None:
        self.pause()
        self.display.show_pivot = False
        self.display.set_word("SFARSIT")
        self.current_idx = len(self.tokens)
        self._save_progress()
        self._update_progress()

    # -------------------------------------------------------------- readouts
    def _update_progress(self) -> None:
        total = max(1, len(self.tokens))
        self.progress.setValue(int(self.current_idx / total * 1000))
        self.position.setText(f"{self.current_idx} / {total}")

    def _update_hud(self) -> None:
        penalty = self.wpm.last_instruction_penalty
        eye = self.wpm.eye_penalty
        effective = self.wpm.last_effective_wpm
        self.hud.setText(
            f"setat {self.wpm.base_wpm}   -   carte {penalty}   "
            f"-   ochi {eye}   =   {effective} WPM")

    def _save_progress(self) -> None:
        if self.book_meta:
            self.db.update_progress(self.book_meta["id"], self.current_idx)

    # -------------------------------------------------------------- controls
    def set_base_wpm(self, wpm: int) -> None:
        self.wpm.set_base(wpm)
        self._update_hud()

    def hw_select(self) -> None:
        self.toggle_pause()

    def hw_wpm_delta(self, delta: int) -> None:
        new_value = self.wpm.nudge(delta)
        self.db.update_setting("base_wpm", str(new_value))
        self._update_hud()

    def wheelEvent(self, event):
        """Mouse wheel stands in for the potentiometer during local testing."""
        notches = event.angleDelta().y() / 120.0
        if notches:
            self.hw_wpm_delta(int(notches * 10))
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.toggle_pause()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Left:
            self.skip(-10)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Right:
            self.skip(10)
            event.accept()
            return
        super().keyPressEvent(event)
