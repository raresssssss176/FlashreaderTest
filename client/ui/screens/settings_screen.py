"""
client/ui/screens/settings_screen.py
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QScrollArea, QSlider, QVBoxLayout,
                             QWidget)

from client.ui.screens.base_screen import BaseScreen


class SettingsScreen(BaseScreen):
    title = "SETARI"

    def __init__(self, router):
        super().__init__(router)
        self.db = router.db

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QVBoxLayout(content)
        form.setSpacing(6)
        form.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(content)
        self.body.addWidget(scroll)

        # ---- reading speed -------------------------------------------------
        self.wpm_label = QLabel("", content)
        form.addWidget(self.wpm_label)
        self.wpm_slider = QSlider(Qt.Orientation.Horizontal, content)
        self.wpm_slider.setRange(100, 900)
        self.wpm_slider.setSingleStep(10)
        self.wpm_slider.setPageStep(50)
        self.wpm_slider.valueChanged.connect(self._on_wpm_changed)
        form.addWidget(self.wpm_slider)

        hint = QLabel("Pe dispozitiv aceasta valoare vine de la potentiometru.", content)
        hint.setObjectName("hint")
        form.addWidget(hint)

        # ---- comprehension assist -----------------------------------------
        self.gain_label = QLabel("", content)
        form.addWidget(self.gain_label)
        self.gain_slider = QSlider(Qt.Orientation.Horizontal, content)
        self.gain_slider.setRange(0, 200)  # percent
        self.gain_slider.setSingleStep(10)
        self.gain_slider.valueChanged.connect(self._on_gain_changed)
        form.addWidget(self.gain_slider)

        gain_hint = QLabel(
            "Cat de mult conteaza instructiunile cartii. 0% = viteza constanta.",
            content)
        gain_hint.setObjectName("hint")
        form.addWidget(gain_hint)

        # ---- font size -----------------------------------------------------
        self.font_label = QLabel("", content)
        form.addWidget(self.font_label)
        self.font_slider = QSlider(Qt.Orientation.Horizontal, content)
        self.font_slider.setRange(28, 110)
        self.font_slider.valueChanged.connect(self._on_font_changed)
        form.addWidget(self.font_slider)

        # ---- toggles -------------------------------------------------------
        self.night_cb = QCheckBox("Mod noapte", content)
        self.night_cb.toggled.connect(self._on_night_toggled)
        form.addWidget(self.night_cb)

        self.anim_cb = QCheckBox("Animatii la schimbarea cuvantului", content)
        self.anim_cb.toggled.connect(
            lambda v: self.db.update_setting("animations", "true" if v else "false"))
        form.addWidget(self.anim_cb)

        self.focus_cb = QCheckBox("Litera de focalizare colorata (ORP)", content)
        self.focus_cb.toggled.connect(
            lambda v: self.db.update_setting("focus_letter", "true" if v else "false"))
        form.addWidget(self.focus_cb)

        self.hud_cb = QCheckBox("Afiseaza WPM in timpul lecturii", content)
        self.hud_cb.toggled.connect(
            lambda v: self.db.update_setting("show_hud", "true" if v else "false"))
        form.addWidget(self.hud_cb)

        self.virtual_cb = QCheckBox("Butoane virtuale (test fara hardware)", content)
        self.virtual_cb.toggled.connect(self._on_virtual_toggled)
        form.addWidget(self.virtual_cb)

        self.eye_cb = QCheckBox("Camera / eye tracking (dezactivat in test local)", content)
        self.eye_cb.toggled.connect(
            lambda v: self.db.update_setting("eye_tracking_enabled", "true" if v else "false"))
        form.addWidget(self.eye_cb)

        # ---- server --------------------------------------------------------
        form.addWidget(QLabel("Adresa server:", content))
        server_row = QHBoxLayout()
        self.server_edit = QLineEdit(content)
        self.server_edit.setPlaceholderText("http://127.0.0.1:8000")
        server_row.addWidget(self.server_edit, 1)
        save_btn = QPushButton("SALVEAZA", content)
        save_btn.setFixedWidth(140)
        save_btn.clicked.connect(self._save_server)
        server_row.addWidget(save_btn)
        form.addLayout(server_row)

        self.server_status = QLabel("", content)
        self.server_status.setObjectName("hint")
        form.addWidget(self.server_status)

    # ------------------------------------------------------------- lifecycle
    def on_enter(self) -> None:
        self.wpm_slider.setValue(int(self.db.get_setting("base_wpm", "300")))
        self.gain_slider.setValue(int(float(self.db.get_setting("instruction_gain", "1.0")) * 100))
        self.font_slider.setValue(int(self.db.get_setting("font_size", "56")))
        self.night_cb.setChecked(self.db.get_setting("night_mode", "false") == "true")
        self.anim_cb.setChecked(self.db.get_setting("animations", "true") == "true")
        self.focus_cb.setChecked(self.db.get_setting("focus_letter", "true") == "true")
        self.hud_cb.setChecked(self.db.get_setting("show_hud", "true") == "true")
        self.virtual_cb.setChecked(self.db.get_setting("show_virtual_controls", "true") == "true")
        self.eye_cb.setChecked(self.db.get_setting("eye_tracking_enabled", "false") == "true")
        self.server_edit.setText(self.db.get_setting("server_url", "http://127.0.0.1:8000"))
        self._refresh_labels()

    def _refresh_labels(self) -> None:
        self.wpm_label.setText(f"Viteza de baza: {self.wpm_slider.value()} WPM")
        self.gain_label.setText(f"Asistenta la intelegere: {self.gain_slider.value()}%")
        self.font_label.setText(f"Marime text: {self.font_slider.value()} px")

    # ---------------------------------------------------------------- slots
    def _on_wpm_changed(self, value: int) -> None:
        self.db.update_setting("base_wpm", str(value))
        self.router.reader_screen.set_base_wpm(value)
        self._refresh_labels()

    def _on_gain_changed(self, value: int) -> None:
        self.db.update_setting("instruction_gain", str(value / 100.0))
        self.router.reader_screen.wpm.instruction_gain = value / 100.0
        self._refresh_labels()

    def _on_font_changed(self, value: int) -> None:
        self.db.update_setting("font_size", str(value))
        self._refresh_labels()

    def _on_night_toggled(self, checked: bool) -> None:
        self.db.update_setting("night_mode", "true" if checked else "false")
        self.router.apply_theme()

    def _on_virtual_toggled(self, checked: bool) -> None:
        self.db.update_setting("show_virtual_controls", "true" if checked else "false")
        self.router.virtual_controls.setVisible(checked)

    def _save_server(self) -> None:
        url = self.server_edit.text().strip() or "http://127.0.0.1:8000"
        self.db.update_setting("server_url", url)
        self.server_status.setText(f"Salvat: {url}")

    # Sliders should react to the potentiometer, not steal focus navigation.
    def hw_wpm_delta(self, delta: int) -> None:
        widget = self.focusWidget()
        if isinstance(widget, QSlider):
            widget.setValue(widget.value() + (10 if delta > 0 else -10))
        else:
            super().hw_wpm_delta(delta)
