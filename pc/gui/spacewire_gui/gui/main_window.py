"""Main application window."""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from spacewire_gui.backend.base import SpaceWireBackend
from spacewire_gui.backend.mock_backend import MockSpaceWireBackend
from spacewire_gui.gui.app_icon import load_app_icon
from spacewire_gui.gui.widgets.camera_panel import CameraPanel
from spacewire_gui.gui.widgets.debug_panel import DebugPanel
from spacewire_gui.gui.widgets.housekeeping_panel import HousekeepingPanel
from spacewire_gui.gui.widgets.link_panel import LinkPanel
from spacewire_gui.gui.widgets.log_panel import LogPanel
from spacewire_gui.models.spacewire_status import SpaceWireStatus


class MainWindow(QMainWindow):
    def __init__(self, backend: SpaceWireBackend, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._mock_backend = backend if isinstance(backend, MockSpaceWireBackend) else None

        self.setWindowTitle("SpaceWire Camera Control")
        self.setWindowIcon(load_app_icon())
        self.setMinimumSize(1000, 880)
        self.resize(1100, 1000)

        self._link_panel = LinkPanel()
        self._camera_panel = CameraPanel()
        self._housekeeping_panel = HousekeepingPanel()
        self._log_panel = LogPanel()
        self._debug_panel = DebugPanel()
        self._debug_panel.setVisible(False)

        self._build_layout()
        self._build_menu()
        self._connect_backend()
        self._connect_panels()

        initial_status = backend.get_status()
        self._on_status_updated(initial_status)
        self.statusBar().showMessage(f"{backend.backend_name} backend active")

    def _build_layout(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        self._link_panel.setMinimumWidth(240)
        self._link_panel.setMaximumWidth(300)
        top_row.addWidget(self._link_panel)
        top_row.addWidget(self._camera_panel, stretch=1)

        root.addLayout(top_row, stretch=1)
        root.addWidget(self._housekeeping_panel)
        root.addWidget(self._debug_panel)
        root.addWidget(self._log_panel)
        self._log_panel.setMaximumHeight(140)

        self.setCentralWidget(central)

    def _build_menu(self) -> None:
        view_menu = self.menuBar().addMenu("View")
        self._log_action = QAction("Event Log", self)
        self._log_action.setCheckable(True)
        self._log_action.setChecked(True)
        self._log_action.toggled.connect(self._log_panel.setVisible)
        view_menu.addAction(self._log_action)

        self._debug_action = QAction("Simulation / Debug", self)
        self._debug_action.setCheckable(True)
        self._debug_action.setEnabled(self._mock_backend is not None)
        self._debug_action.toggled.connect(self._debug_panel.setVisible)
        view_menu.addAction(self._debug_action)

    def _connect_backend(self) -> None:
        self._backend.status_updated.connect(self._on_status_updated)
        self._backend.busy_changed.connect(self._on_busy_changed)
        self._backend.image_received.connect(self._camera_panel.set_image)
        self._backend.housekeeping_updated.connect(self._housekeeping_panel.set_snapshot)
        self._backend.housekeeping_request_finished.connect(
            self._housekeeping_panel.set_request_status
        )
        self._backend.log_message.connect(self._log_panel.append_message)
        self._backend.connection_error.connect(self._log_panel.append_message)

    def _connect_panels(self) -> None:
        self._link_panel.connect_requested.connect(self._backend.connect_spacewire)
        self._link_panel.disconnect_requested.connect(self._backend.disconnect_spacewire)
        self._camera_panel.pattern_changed.connect(self._backend.set_pattern)
        self._camera_panel.capture_requested.connect(self._backend.request_image)
        self._housekeeping_panel.refresh_requested.connect(
            self._backend.request_housekeeping
        )

        if self._mock_backend is not None:
            self._debug_panel.disconnect_error_toggled.connect(
                lambda enabled: self._mock_backend.set_simulated_error("disconnect_error", enabled)
            )
            self._debug_panel.parity_error_toggled.connect(
                lambda enabled: self._mock_backend.set_simulated_error("parity_error", enabled)
            )
            self._debug_panel.escape_error_toggled.connect(
                lambda enabled: self._mock_backend.set_simulated_error("escape_error", enabled)
            )
            self._debug_panel.credit_error_toggled.connect(
                lambda enabled: self._mock_backend.set_simulated_error("credit_error", enabled)
            )
            self._debug_panel.simulate_rx_valid_requested.connect(self._mock_backend.simulate_rx_valid)
            self._debug_panel.clear_errors_requested.connect(self._on_clear_errors)

    def _on_status_updated(self, status: SpaceWireStatus) -> None:
        self._link_panel.set_busy(self._backend.is_busy)
        self._link_panel.update_status(status)
        self._camera_panel.update_status(status)
        self._housekeeping_panel.update_status(status)

    def _on_busy_changed(self) -> None:
        self._link_panel.set_busy(self._backend.is_busy)
        self._link_panel.update_status(self._backend.get_status())

    def _on_clear_errors(self) -> None:
        if self._mock_backend is not None:
            self._mock_backend.clear_errors()
            self._debug_panel.reset()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._backend.shutdown()
        super().closeEvent(event)
