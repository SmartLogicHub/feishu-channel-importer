"""Reusable small UI building blocks."""
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QVBoxLayout,
)


class Card(QFrame):
    def __init__(self, title: str = "", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(33, 56, 92, 24))
        self.setGraphicsEffect(shadow)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("sectionTitle")
            self.layout.addWidget(label)
        if subtitle:
            label = QLabel(subtitle)
            label.setObjectName("muted")
            label.setWordWrap(True)
            self.layout.addWidget(label)


def page_heading(title: str, subtitle: str):
    frame = QFrame()
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 4)
    layout.setSpacing(4)
    title_label = QLabel(title)
    title_label.setObjectName("pageTitle")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("muted")
    subtitle_label.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    return frame
