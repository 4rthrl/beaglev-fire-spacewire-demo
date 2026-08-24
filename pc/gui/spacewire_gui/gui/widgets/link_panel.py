"""SpaceWire link status and connection controls."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from spacewire_gui.gui.widgets.status_indicator import StatusIndicator
from spacewire_gui.models.spacewire_status import LinkConnectionState, SpaceWireStatus


class LinkPanel(QGroupBox):
    connect_requested = Signal()
    disconnect_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("SPACEWIRE LINK", parent)
        self._busy = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._summary_row = QWidget()
        summary_layout = QHBoxLayout(self._summary_row)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        self._summary_dot = QLabel()
        self._summary_dot.setFixedSize(12, 12)
        self._summary_dot.setStyleSheet("background-color: #22c55e; border-radius: 6px;")
        self._summary_label = QLabel("Running")
        self._summary_label.setObjectName("ConnectionSummary")
        summary_layout.addWidget(self._summary_dot)
        summary_layout.addWidget(self._summary_label)
        summary_layout.addStretch(1)
        self._summary_row.setVisible(False)
        layout.addWidget(self._summary_row)

        self._parity_error = StatusIndicator("Parity")
        self._escape_error = StatusIndicator("Escape")
        self._credit_error = StatusIndicator("Credit")
        for indicator in (
            self._parity_error,
            self._escape_error,
            self._credit_error,
        ):
            layout.addWidget(indicator)

        layout.addStretch(1)

        self._connect_button = QPushButton("Connect")
        self._connect_button.setObjectName("PrimaryButton")
        self._connect_button.setFixedHeight(32)
        self._connect_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._connect_button.clicked.connect(self._on_connect_button_clicked)
        layout.addWidget(self._connect_button)

    def _on_connect_button_clicked(self) -> None:
        if self._connect_button.text() == "Disconnect":
            self.disconnect_requested.emit()
        else:
            self.connect_requested.emit()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy

    def update_status(self, status: SpaceWireStatus) -> None:
        self._update_summary(status)

        self._parity_error.set_state(*StatusIndicator.error_state(status.parity_error))
        self._escape_error.set_state(*StatusIndicator.error_state(status.escape_error))
        self._credit_error.set_state(*StatusIndicator.error_state(status.credit_error))

        self._refresh_connect_button(status)

    def _update_summary(self, status: SpaceWireStatus) -> None:
        self._summary_row.setVisible(status.running)

    def _refresh_connect_button(self, status: SpaceWireStatus) -> None:
        link = status.link_state()

        if self._busy or link == LinkConnectionState.CONNECTING:
            self._connect_button.setText("Connecting...")
            self._connect_button.setEnabled(False)
            self._apply_button_style("PrimaryButton")
            return

        if status.running or link == LinkConnectionState.CONNECTED:
            self._connect_button.setText("Disconnect")
            self._connect_button.setEnabled(True)
            self._apply_button_style("SecondaryButton")
            return

        self._connect_button.setText("Connect")
        self._connect_button.setEnabled(True)
        if status.has_operator_errors():
            self._apply_button_style("WarningButton")
        else:
            self._apply_button_style("PrimaryButton")

    def _apply_button_style(self, object_name: str) -> None:
        self._connect_button.setObjectName(object_name)
        self._connect_button.style().unpolish(self._connect_button)
        self._connect_button.style().polish(self._connect_button)
