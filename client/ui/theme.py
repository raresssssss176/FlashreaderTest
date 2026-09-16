"""
client/ui/theme.py

One place for colours, sizes and the global stylesheet. Touch targets are
kept at 48px minimum so they stay usable with a finger on a small screen.
"""

DARK = {
    "bg": "#101014",
    "surface": "#1B1B21",
    "surface_alt": "#26262E",
    "text": "#F2F2F5",
    "text_dim": "#8A8A99",
    "accent": "#00E676",
    "accent_dim": "#00794A",
    "danger": "#FF5252",
    "pivot": "#FF3D57",
}

LIGHT = {
    "bg": "#FAFAF7",
    "surface": "#FFFFFF",
    "surface_alt": "#ECECE6",
    "text": "#15151A",
    "text_dim": "#6A6A72",
    "accent": "#00A85A",
    "accent_dim": "#7FD3AC",
    "danger": "#C62828",
    "pivot": "#D8002A",
}

TOUCH_HEIGHT = 56


def palette(night_mode: bool) -> dict:
    return DARK if night_mode else LIGHT


def stylesheet(night_mode: bool) -> str:
    c = palette(night_mode)
    return f"""
    QWidget {{
        background-color: {c['bg']};
        color: {c['text']};
        font-family: "DejaVu Sans", "Segoe UI", Arial, sans-serif;
    }}
    QLabel#screenTitle {{
        font-size: 22px;
        font-weight: bold;
        color: {c['text']};
    }}
    QLabel#hint {{
        color: {c['text_dim']};
        font-size: 13px;
    }}
    QPushButton {{
        background-color: {c['surface']};
        color: {c['text']};
        font-size: 18px;
        border: 1px solid {c['surface_alt']};
        border-radius: 10px;
        padding: 14px;
        min-height: {TOUCH_HEIGHT - 28}px;
    }}
    QPushButton:hover {{
        border-color: {c['accent']};
    }}
    QPushButton:focus {{
        border: 2px solid {c['accent']};
        background-color: {c['surface_alt']};
    }}
    QPushButton:pressed {{
        background-color: {c['accent']};
        color: {c['bg']};
    }}
    QPushButton#primary {{
        background-color: {c['accent']};
        color: {c['bg']};
        font-weight: bold;
    }}
    QPushButton#ghost {{
        background-color: transparent;
        border: 1px solid {c['surface_alt']};
        font-size: 16px;
        padding: 10px 14px;
    }}
    QPushButton#danger {{
        background-color: transparent;
        color: {c['danger']};
        border: 1px solid {c['danger']};
    }}
    QScrollArea {{ border: none; }}
    QLineEdit {{
        background-color: {c['surface']};
        border: 1px solid {c['surface_alt']};
        border-radius: 8px;
        padding: 10px;
        font-size: 16px;
    }}
    QSlider::groove:horizontal {{
        height: 8px;
        background: {c['surface_alt']};
        border-radius: 4px;
    }}
    QSlider::handle:horizontal {{
        background: {c['accent']};
        width: 26px;
        margin: -10px 0;
        border-radius: 13px;
    }}
    QCheckBox {{ font-size: 17px; padding: 10px; }}
    QProgressBar {{
        background: {c['surface_alt']};
        border: none;
        border-radius: 3px;
        height: 6px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background: {c['accent']};
        border-radius: 3px;
    }}
    """
