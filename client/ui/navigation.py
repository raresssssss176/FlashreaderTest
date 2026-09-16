"""
client/ui/navigation.py

Stacked router. Owns the screen stack, the navigation history and the
hardware bus, and keeps the virtual control strip pinned at the bottom.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from client.core.hardware import HardwareBus
from client.db.database import LocalDatabase
from client.ui.screens.home_screen import HomeScreen
from client.ui.screens.library_screen import LibraryScreen
from client.ui.screens.reader_screen import ReaderScreen
from client.ui.screens.settings_screen import SettingsScreen
from client.ui.screens.store_screen import StoreScreen
from client.ui.widgets.virtual_controls import VirtualControls

HOME, LIBRARY, STORE, SETTINGS, READER = 0, 1, 2, 3, 4


class NavigationRouter(QWidget):
    def __init__(self, bus: HardwareBus = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FlashReader")
        self.db = LocalDatabase()
        self.bus = bus or HardwareBus(self)

        self.stack = QStackedWidget(self)

        self.home_screen = HomeScreen(self)
        self.library_screen = LibraryScreen(self)
        self.store_screen = StoreScreen(self)
        self.settings_screen = SettingsScreen(self)
        self.reader_screen = ReaderScreen(self)

        for screen in (self.home_screen, self.library_screen, self.store_screen,
                       self.settings_screen, self.reader_screen):
            self.stack.addWidget(screen)

        self.virtual_controls = VirtualControls(self.bus, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stack, 1)
        layout.addWidget(self.virtual_controls)

        show_virtual = self.db.get_setting("show_virtual_controls", "true") == "true"
        self.virtual_controls.setVisible(show_virtual)

        # Physical controls -> whatever screen is on top
        self.bus.select.connect(self._on_select)
        self.bus.back.connect(self.go_back)
        self.bus.wpm_delta.connect(self._on_wpm_delta)
        self.bus.wpm_absolute.connect(self._on_wpm_absolute)

        self._history = []
        self.stack.setCurrentIndex(HOME)
        self.home_screen.on_enter()

    # ------------------------------------------------------------ navigation
    def current_screen(self):
        return self.stack.currentWidget()

    def navigate_to(self, index: int, remember: bool = True) -> None:
        current = self.stack.currentIndex()
        if index == current:
            return

        self.current_screen().on_leave()
        if remember:
            self._history.append(current)

        self.stack.setCurrentIndex(index)
        screen = self.current_screen()
        screen.on_enter()
        screen.focus_first()

    def go_back(self) -> None:
        """Touch BACK button and the physical hold both land here."""
        if not self._history:
            if self.stack.currentIndex() != HOME:
                self.navigate_to(HOME, remember=False)
            return

        self.current_screen().on_leave()
        previous = self._history.pop()
        self.stack.setCurrentIndex(previous)
        screen = self.current_screen()
        screen.on_enter()
        screen.focus_first()

    def go_home(self) -> None:
        self._history.clear()
        self.navigate_to(HOME, remember=False)

    # -------------------------------------------------------------- hardware
    def _on_select(self) -> None:
        self.current_screen().hw_select()

    def _on_wpm_delta(self, delta: int) -> None:
        self.current_screen().hw_wpm_delta(delta)

    def _on_wpm_absolute(self, wpm: int) -> None:
        """Potentiometer reports an absolute position, not a delta."""
        self.db.update_setting("base_wpm", str(wpm))
        if self.stack.currentIndex() == READER:
            self.reader_screen.set_base_wpm(wpm)

    # ---------------------------------------------------------------- extras
    def open_book(self, book_id: str) -> bool:
        """Used by Home (continue) and Library (pick a title)."""
        result = self.db.get_book_payload(book_id)
        book_meta, tokens = result
        if not book_meta or not tokens:
            return False
        self.reader_screen.load_book(book_meta, tokens)
        self.navigate_to(READER)
        return True

    def apply_theme(self) -> None:
        from client.ui.theme import stylesheet
        night = self.db.get_setting("night_mode", "false") == "true"
        app = self.window()
        app.setStyleSheet(stylesheet(night))

    def keyPressEvent(self, event):
        """Keyboard shortcuts so the device is testable on a laptop."""
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.go_back()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_select()
        elif key == Qt.Key.Key_Up:
            self._on_wpm_delta(10)
        elif key == Qt.Key.Key_Down:
            self._on_wpm_delta(-10)
        else:
            super().keyPressEvent(event)
