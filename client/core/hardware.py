"""
client/core/hardware.py

Hardware abstraction layer.

The device has exactly three inputs: a touch screen, one button
(press = select, hold = back) and a potentiometer (WPM). Everything in
the UI listens to HardwareBus, never to the GPIO directly, so the same
code runs on a laptop with a mouse wheel and on the Pi with the real
MCP3008 wired up as in the schematic.
"""

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

HOLD_MS = 600  # press longer than this and it counts as a hold


class HardwareBus(QObject):
    """Every physical (or simulated) input lands here."""

    select = pyqtSignal()           # short press
    back = pyqtSignal()             # long press / hold
    wpm_delta = pyqtSignal(int)     # relative WPM change (mouse wheel)
    wpm_absolute = pyqtSignal(int)  # absolute WPM (potentiometer position)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._on_hold)
        self._hold_fired = False

    # Called on button-down / button-up, whether from GPIO or a virtual button
    def press_started(self) -> None:
        self._hold_fired = False
        self._hold_timer.start(HOLD_MS)

    def press_released(self) -> None:
        self._hold_timer.stop()
        if not self._hold_fired:
            self.select.emit()

    def _on_hold(self) -> None:
        self._hold_fired = True
        self.back.emit()


class GpioAdapter(QObject):
    """
    Real hardware driver: one button on a GPIO pin, one potentiometer on
    channel 0 of the MCP3008 (SPI0), matching the KiCad schematic.

    Safe to construct on any machine: if RPi.GPIO / spidev are missing it
    simply reports unavailable and the app runs on virtual controls.
    """

    def __init__(self, bus: HardwareBus, button_pin: int = 17,
                 adc_channel: int = 0, min_wpm: int = 100, max_wpm: int = 900,
                 parent=None):
        super().__init__(parent)
        self.bus = bus
        self.button_pin = button_pin
        self.adc_channel = adc_channel
        self.min_wpm = min_wpm
        self.max_wpm = max_wpm
        self.available = False
        self._spi = None
        self._last_sent = None

        try:
            import RPi.GPIO as GPIO  # noqa: N814
            import spidev

            self._GPIO = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(button_pin, GPIO.BOTH,
                                  callback=self._on_edge, bouncetime=20)

            self._spi = spidev.SpiDev()
            self._spi.open(0, 0)
            self._spi.max_speed_hz = 1350000

            self._poll = QTimer(self)
            self._poll.timeout.connect(self._read_pot)
            self._poll.start(120)

            self.available = True
        except Exception:
            # No Pi, no GPIO, no problem - virtual controls take over.
            self.available = False

    def _on_edge(self, channel) -> None:
        # Button wired to ground with an internal pull-up: LOW means pressed.
        if self._GPIO.input(self.button_pin) == 0:
            self.bus.press_started()
        else:
            self.bus.press_released()

    def _read_pot(self) -> None:
        if not self._spi:
            return
        try:
            raw = self._spi.xfer2([1, (8 + self.adc_channel) << 4, 0])
            value = ((raw[1] & 3) << 8) + raw[2]  # 0..1023
        except Exception:
            return

        wpm = self.min_wpm + int((value / 1023.0) * (self.max_wpm - self.min_wpm))
        wpm = int(round(wpm / 5.0) * 5)  # quantise, ADC noise is real
        if wpm != self._last_sent:
            self._last_sent = wpm
            self.bus.wpm_absolute.emit(wpm)

    def close(self) -> None:
        try:
            if self._spi:
                self._spi.close()
            if self.available:
                self._GPIO.cleanup()
        except Exception:
            pass
