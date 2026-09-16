"""
client/ui/navigation.py

Stacked router to manage transitions between ui screens.
"""

from PyQt6.QtWidgets import QStackedWidget, QWidget, QVBoxLayout
from client.ui.screens.home_screen import HomeScreen
from client.ui.screens.library_screen import LibraryScreen
from client.ui.screens.store_screen import StoreScreen
from client.ui.screens.settings_screen import SettingsScreen
from client.ui.screens.reader_screen import ReaderScreen


class NavigationRouter(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Screen Index Map:
        # 0: HOME, 1: LIBRARY (CONTINUA), 2: STORE (MAGAZIN), 3: SETTINGS, 4: READER
        self.home_screen = HomeScreen(self)
        self.library_screen = LibraryScreen(self)
        self.store_screen = StoreScreen(self)
        self.settings_screen = SettingsScreen(self)
        self.reader_screen = ReaderScreen(self)

        self.addWidget(self.home_screen)      # Index 0
        self.addWidget(self.library_screen)   # Index 1
        self.addWidget(self.store_screen)     # Index 2
        self.addWidget(self.settings_screen)  # Index 3
        self.addWidget(self.reader_screen)    # Index 4

        self.setCurrentIndex(0)

    def navigate_to(self, index: int):
        if index == 1:
            self.library_screen.refresh_library()
        self.setCurrentIndex(index)

    def handle_back(self):
        """Hardware hold button triggers return to Home."""
        if self.currentIndex() != 0:
            self.setCurrentIndex(0)