"""Locate and load the application icon in source and PyInstaller builds."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative


def application_icon() -> QIcon:
    return QIcon(str(resource_path("resources/icon.ico")))
