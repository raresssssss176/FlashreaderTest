"""
client/main.py
"""

import sys
from pathlib import Path

# Ensure project root is in python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from client.db.database import LocalDatabase
from client.ui.navigation import NavigationRouter


def main():
    # 1. Initialize local SQLite database schema and seed defaults
    db = LocalDatabase()

    # 2. Launch PyQt Application
    app = QApplication(sys.argv)

    # 3. Instantiate and display the navigation router stack
    router = NavigationRouter()
    router.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()