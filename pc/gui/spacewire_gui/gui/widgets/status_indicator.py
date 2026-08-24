"""Reusable boolean/error status row with colored indicator and text."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget


class IndicatorState(Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    WARNING = "warning"
    ERROR = "error"


_STATE_COLORS = {
    IndicatorState.INACTIVE: "#9ca3af",
    IndicatorState.ACTIVE: "#22c55e",
    IndicatorState.WARNING: "#f59e0b",
    IndicatorState.ERROR: "#ef4444",
}


class StatusIndicator(QWidget):
    def __init__(
        self,
        label: str,
        parent: QWidget | None = None,
        *,
        monospace_value: bool = False,
    ) -> None:
        super().__init__(parent)
        self._label_text = label

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(8)

        self._dot = QLabel()
        self._dot.setFixedSize(10, 10)
        self._dot.setStyleSheet("background-color: #9ca3af; border-radius: 5px;")

        self._name = QLabel(label)
        self._name.setObjectName("MutedLabel")
        self._name.setMinimumWidth(110)

        self._value = QLabel("—")
        self._value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._value.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if monospace_value:
            self._value.setObjectName("MonospaceValue")

        layout.addWidget(self._dot)
        layout.addWidget(self._name)
        layout.addStretch(1)
        layout.addWidget(self._value)

    def set_state(self, state: IndicatorState, text: str) -> None:
        color = _STATE_COLORS[state]
        self._dot.setStyleSheet(
            f"background-color: {color}; border-radius: 5px;"
        )
        self._value.setText(text)

    @staticmethod
    def bool_state(active: bool, *, active_text: str = "YES", inactive_text: str = "NO") -> tuple[IndicatorState, str]:
        if active:
            return IndicatorState.ACTIVE, active_text
        return IndicatorState.INACTIVE, inactive_text

    @staticmethod
    def error_state(has_error: bool) -> tuple[IndicatorState, str]:
        if has_error:
            return IndicatorState.ERROR, "ERROR"
        return IndicatorState.ACTIVE, "OK"
