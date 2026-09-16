"""
client/ui/screens/base_screen.py

Common behaviour for every screen: a nav bar with a touch BACK button,
lifecycle hooks, and default handling of the physical controls.

Screens override:
    on_enter()        - called every time the screen becomes visible
    on_leave()        - called when navigating away (save state here)
    hw_select()       - physical button, short press
    hw_wpm_delta(d)   - potentiometer / mouse wheel
"""

from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from client.ui.widgets.nav_bar import NavBar


class BaseScreen(QWidget):
    #: shown in the nav bar; None hides the bar entirely (reader screen)
    title = ""
    show_nav_bar = True

    def __init__(self, router):
        super().__init__()
        self.router = router

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(18, 14, 18, 10)
        self.root.setSpacing(10)

        self.nav_bar = None
        if self.show_nav_bar:
            self.nav_bar = NavBar(self.title, self.router.go_back, self)
            self.root.addWidget(self.nav_bar)

        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        self.root.addLayout(self.body, 1)

    # ------------------------------------------------------------- lifecycle
    def on_enter(self) -> None:
        pass

    def on_leave(self) -> None:
        pass

    # -------------------------------------------------------------- hardware
    def hw_select(self) -> None:
        """Short press activates whatever currently has focus."""
        widget = self.focusWidget()
        if isinstance(widget, QPushButton):
            widget.click()
        else:
            self.focus_first()

    def hw_wpm_delta(self, delta: int) -> None:
        """
        Outside the reader the potentiometer is the most natural way to
        move the selection up and down a menu.
        """
        if delta > 0:
            self.focusNextChild()
        else:
            self.focusPreviousChild()

    def focus_first(self) -> None:
        for child in self.findChildren(QPushButton):
            if child.isVisible() and child.isEnabled():
                child.setFocus()
                return
