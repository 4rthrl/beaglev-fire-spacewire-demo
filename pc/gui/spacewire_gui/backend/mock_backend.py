"""Simulated SpaceWire backend for offline development on Windows."""

from __future__ import annotations

import random
from typing import Literal

from PySide6.QtCore import QTimer

from spacewire_gui.backend.base import SpaceWireBackend
from spacewire_gui.backend.test_patterns import IMAGE_HEIGHT, IMAGE_WIDTH, generate_pattern
from spacewire_gui.models.image_patterns import ALL_PATTERNS, PATTERN_LABELS, SOLID_RED
from spacewire_gui.models.spacewire_status import SpaceWireStatus

ErrorField = Literal["disconnect_error", "parity_error", "escape_error", "credit_error"]


class MockSpaceWireBackend(SpaceWireBackend):
    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self._status = self._initial_status()
        self._connect_timer = QTimer(self)
        self._connect_timer.setSingleShot(True)
        self._connect_timer.timeout.connect(self._finish_connect)

        self._image_timer = QTimer(self)
        self._image_timer.setSingleShot(True)
        self._image_timer.timeout.connect(self._finish_image_request)

        self._pending_pattern: int | None = None
        self._selected_pattern = SOLID_RED
        self._operation_in_progress = False

    @property
    def backend_name(self) -> str:
        return "Mock"

    @property
    def is_busy(self) -> bool:
        return self._operation_in_progress

    def get_status(self) -> SpaceWireStatus:
        return self._status.copy()

    def connect_spacewire(self) -> None:
        if self._operation_in_progress:
            return
        if self._status.running or self._status.connecting:
            return

        self._operation_in_progress = True
        self._status.started = True
        self._status.connecting = True
        self._status.running = False
        self._emit_status()
        self.log_message.emit("Connect requested")

        delay_ms = random.randint(500, 1000)
        self._connect_timer.start(delay_ms)

    def disconnect_spacewire(self) -> None:
        if self._operation_in_progress and not self._status.connecting:
            return
        if not self._status.started and not self._status.running and not self._status.connecting:
            return

        self._connect_timer.stop()
        self._image_timer.stop()
        self._pending_pattern = None
        self._operation_in_progress = False

        self._status = self._disconnected_status()
        self._emit_status()
        self.log_message.emit("SpaceWire disconnected")

    def set_pattern(self, pattern: int) -> None:
        if pattern not in ALL_PATTERNS:
            self.connection_error.emit(f"Invalid pattern: {pattern}")
            return
        self._selected_pattern = pattern
        label = PATTERN_LABELS.get(pattern, f"Pattern {pattern}")
        self.log_message.emit(f"Pattern set: {label}")

    def request_image(self, pattern: int) -> None:
        if not self._status.running or self._status.connecting:
            self.connection_error.emit("Image request rejected: link not running")
            return
        if self._image_timer.isActive():
            return

        self._selected_pattern = pattern
        label = PATTERN_LABELS.get(pattern, f"Pattern {pattern}")
        self.log_message.emit(f"{label} image requested")

        self._pending_pattern = pattern
        delay_ms = random.randint(300, 700)
        self._image_timer.start(delay_ms)

    def set_simulated_error(self, field: ErrorField, enabled: bool) -> None:
        setattr(self._status, field, enabled)
        self._status.sync_errors_raw()
        self._emit_status()
        label = field.replace("_", " ")
        state = "enabled" if enabled else "cleared"
        self.log_message.emit(f"Simulated {label} {state}")

    def simulate_rx_valid(self) -> None:
        self._status.rx_valid = True
        self._emit_status()
        self.log_message.emit("Simulated RX valid")

    def clear_errors(self) -> None:
        self._status.disconnect_error = False
        self._status.parity_error = False
        self._status.escape_error = False
        self._status.credit_error = False
        self._status.sync_errors_raw()
        self._emit_status()
        self.log_message.emit("Simulated errors cleared")

    def shutdown(self) -> None:
        self._connect_timer.stop()
        self._image_timer.stop()

    def _finish_connect(self) -> None:
        self._operation_in_progress = False
        self._status.started = True
        self._status.connecting = False
        self._status.running = True
        self._status.tx_ready = True
        self._status.control_raw = 0x00000001
        self._status.status_raw = 0x0000000D
        self._emit_status()
        self.log_message.emit("SpaceWire link running")

    def _finish_image_request(self) -> None:
        if self._pending_pattern is None:
            return
        if not self._status.running:
            self._pending_pattern = None
            return

        pattern = self._pending_pattern
        self._pending_pattern = None
        image = generate_pattern(pattern)
        self.image_received.emit(image)
        self.log_message.emit(f"Image received: {IMAGE_WIDTH}x{IMAGE_HEIGHT}")

    def _emit_status(self) -> None:
        self.status_updated.emit(self._status.copy())

    @staticmethod
    def _initial_status() -> SpaceWireStatus:
        return SpaceWireStatus(
            started=False,
            connecting=False,
            running=False,
            tx_ready=True,
            tx_half_full=False,
            rx_valid=False,
            rx_half_full=False,
            disconnect_error=False,
            parity_error=False,
            escape_error=False,
            credit_error=False,
            tx_divider=4,
            control_raw=0x00000000,
            status_raw=0x00000008,
            errors_raw=0x00000000,
            core_id=0x53505731,
        )

    @staticmethod
    def _disconnected_status() -> SpaceWireStatus:
        status = MockSpaceWireBackend._initial_status()
        status.control_raw = 0x00000004
        status.status_raw = 0x00000008
        return status
