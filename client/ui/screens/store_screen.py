from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class StoreScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Store Screen Placeholder"))