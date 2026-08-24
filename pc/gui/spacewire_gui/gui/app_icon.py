"""Application window / taskbar icon."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon


def load_app_icon() -> QIcon:
    icon_path = Path(__file__).resolve().parent / "icons" / "camera.svg"
    return QIcon(str(icon_path))
