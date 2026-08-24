"""Timestamped engineering event log."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QGroupBox, QPlainTextEdit, QVBoxLayout, QWidget


class LogPanel(QGroupBox):
    MAX_LINES = 300

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Event Log", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 6)

        self._text = QPlainTextEdit()
        self._text.setObjectName("LogPanel")
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(self.MAX_LINES)
        layout.addWidget(self._text)

    def append_message(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._text.appendPlainText(f"{timestamp}  {message}")
