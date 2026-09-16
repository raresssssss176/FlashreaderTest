"""
client/core/api_client.py

Thin HTTP client for the FlashReader server. Every call returns
(ok: bool, payload_or_error) so callers never have to catch exceptions.
Network work happens on a worker thread (see NetworkTask) so the touch UI
never freezes while a book downloads.
"""

from typing import Any, Callable, List, Tuple

import requests
from PyQt6.QtCore import QThread, pyqtSignal

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 20


class ApiClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def set_base_url(self, url: str) -> None:
        self.base_url = url.rstrip("/")

    def _get(self, path: str) -> Tuple[bool, Any]:
        try:
            r = requests.get(f"{self.base_url}{path}", timeout=TIMEOUT)
            r.raise_for_status()
            return True, r.json()
        except requests.exceptions.ConnectionError:
            return False, "Serverul nu raspunde. Porneste server/main.py."
        except requests.exceptions.Timeout:
            return False, "Timeout la server."
        except Exception as exc:
            return False, f"Eroare: {exc}"

    def ping(self) -> Tuple[bool, Any]:
        return self._get("/")

    def get_catalog(self) -> Tuple[bool, List[dict]]:
        return self._get("/store/catalog")

    def download_book(self, book_id: str) -> Tuple[bool, Any]:
        """Returns the full payload: id, title, author, tokens."""
        return self._get(f"/store/download/{book_id}")


class NetworkTask(QThread):
    """
    Runs any callable off the UI thread and hands the result back through
    a signal. Used by the store screen for catalog + download.
    """

    finished_ok = pyqtSignal(object)
    finished_err = pyqtSignal(str)

    def __init__(self, fn: Callable[[], Tuple[bool, Any]], parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            ok, payload = self._fn()
        except Exception as exc:
            self.finished_err.emit(str(exc))
            return
        if ok:
            self.finished_ok.emit(payload)
        else:
            self.finished_err.emit(str(payload))
