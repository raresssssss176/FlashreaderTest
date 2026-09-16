"""
client/main.py

Entry point for the device UI.

Local testing (no Pi, no camera, no GPIO):
    python client/main.py
The mouse wheel acts as the potentiometer, and the HW strip at the bottom
of the screen acts as the physical button (SELECT / HOLD).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from client.core.hardware import GpioAdapter, HardwareBus  # noqa: E402
from client.db.database import LocalDatabase  # noqa: E402
from client.ui.navigation import NavigationRouter  # noqa: E402
from client.ui.theme import stylesheet  # noqa: E402

# Official 7" Raspberry Pi touch display
WINDOW_SIZE = (800, 480)


def main() -> int:
    db = LocalDatabase()

    app = QApplication(sys.argv)
    night = db.get_setting("night_mode", "false") == "true"
    app.setStyleSheet(stylesheet(night))

    bus = HardwareBus()
    router = NavigationRouter(bus=bus)
    router.resize(*WINDOW_SIZE)

    # Real GPIO if we are on the Pi, silently skipped otherwise.
    gpio = GpioAdapter(bus)
    if gpio.available:
        router.virtual_controls.setVisible(False)

    # Camera stays off for local testing. To enable later:
    #   from client.core.eye_tracker import EyeTrackerThread
    #   tracker = EyeTrackerThread()
    #   tracker.slowdown_penalty_updated.connect(router.reader_screen.wpm.set_eye_penalty)
    #   tracker.start()

    router.show()
    exit_code = app.exec()
    gpio.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
