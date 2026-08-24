"""Simulation-only debug controls for the mock backend."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DebugPanel(QGroupBox):
    disconnect_error_toggled = Signal(bool)
    parity_error_toggled = Signal(bool)
    escape_error_toggled = Signal(bool)
    credit_error_toggled = Signal(bool)
    simulate_rx_valid_requested = Signal()
    clear_errors_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Simulation / Debug", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        banner = QLabel("Simulation only — not part of the operator interface")
        banner.setObjectName("DebugBanner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        self._disconnect_cb = QCheckBox("Disconnect error")
        self._parity_cb = QCheckBox("Parity error")
        self._escape_cb = QCheckBox("Escape error")
        self._credit_cb = QCheckBox("Credit error")

        self._disconnect_cb.toggled.connect(self.disconnect_error_toggled.emit)
        self._parity_cb.toggled.connect(self.parity_error_toggled.emit)
        self._escape_cb.toggled.connect(self.escape_error_toggled.emit)
        self._credit_cb.toggled.connect(self.credit_error_toggled.emit)

        for checkbox in (
            self._disconnect_cb,
            self._parity_cb,
            self._escape_cb,
            self._credit_cb,
        ):
            layout.addWidget(checkbox)

        button_row = QHBoxLayout()
        rx_button = QPushButton("Simulate RX valid")
        rx_button.setObjectName("PrimaryButton")
        clear_button = QPushButton("Clear errors")
        clear_button.setObjectName("SecondaryButton")
        rx_button.clicked.connect(self.simulate_rx_valid_requested.emit)
        clear_button.clicked.connect(self.clear_errors_requested.emit)
        button_row.addWidget(rx_button)
        button_row.addWidget(clear_button)
        layout.addLayout(button_row)

    def reset(self) -> None:
        for checkbox in (
            self._disconnect_cb,
            self._parity_cb,
            self._escape_cb,
            self._credit_cb,
        ):
            checkbox.blockSignals(True)
            checkbox.setChecked(False)
            checkbox.blockSignals(False)
