"""
client/core/wpm_controller.py

Single source of truth for reading speed.

    effective_wpm = UserSetWPM - InstructionPenalty - EyePenalty

Everything that wants to influence speed (potentiometer, mouse wheel,
book instructions, the camera later on) goes through this object, so the
reader screen never has to know where a number came from.
"""

from typing import Any, Dict

MIN_WPM = 60
MAX_WPM = 1200


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


class WpmController:
    def __init__(self, base_wpm: int = 300, floor_wpm: int = 80):
        # What the user asked for (potentiometer / mouse wheel / settings)
        self.base_wpm = clamp(int(base_wpm), MIN_WPM, MAX_WPM)
        # Never drop below this no matter how many penalties stack up
        self.floor_wpm = floor_wpm
        # Set by the eye tracker. Stays 0 while the camera is disabled.
        self.eye_penalty = 0
        # 0.0 = ignore the book's instructions entirely, 1.0 = full effect,
        # 1.5 = exaggerate them. Exposed in settings as "comprehension assist".
        self.instruction_gain = 1.0
        # Last computed values, for the on-screen HUD
        self.last_effective_wpm = self.base_wpm
        self.last_instruction_penalty = 0

    # ------------------------------------------------------------------ input
    def set_base(self, wpm: int) -> int:
        self.base_wpm = clamp(int(wpm), MIN_WPM, MAX_WPM)
        return self.base_wpm

    def nudge(self, delta: int) -> int:
        """Relative change, used by the mouse wheel and the potentiometer."""
        return self.set_base(self.base_wpm + int(delta))

    def set_eye_penalty(self, penalty: int) -> None:
        self.eye_penalty = max(0, int(penalty))

    # ----------------------------------------------------------------- output
    def effective_wpm(self, instruction_penalty: int = 0) -> int:
        penalty = int(instruction_penalty * self.instruction_gain)
        self.last_instruction_penalty = penalty
        wpm = self.base_wpm - penalty - self.eye_penalty
        self.last_effective_wpm = clamp(wpm, self.floor_wpm, MAX_WPM)
        return self.last_effective_wpm

    def delay_ms(self, token: Dict[str, Any]) -> int:
        """
        How long this token stays on screen.

        token = {"w": "word", "i": <wpm penalty>, "p": <extra pause ms>}
        The extra pause (punctuation, paragraph breaks) is scaled down at
        high speeds, otherwise commas dominate the whole reading rhythm.
        """
        wpm = self.effective_wpm(token.get("i", 0))
        base_delay = 60000.0 / wpm

        pause = token.get("p", 0)
        if pause:
            pause *= min(1.0, 300.0 / max(1, self.base_wpm))

        return int(base_delay + pause)
