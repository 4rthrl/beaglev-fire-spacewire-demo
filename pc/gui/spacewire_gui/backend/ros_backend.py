"""ROS-backed SpaceWire backend relaying worker signals to the GUI thread."""

from __future__ import annotations

from PySide6.QtCore import QThread
from PySide6.QtGui import QImage

from spacewire_gui.backend.base import SpaceWireBackend
from spacewire_gui.backend.ros_constants import THREAD_JOIN_TIMEOUT_MS
from spacewire_gui.backend.ros_worker import RosWorker
from spacewire_gui.models.image_patterns import PATTERN_LABELS
from spacewire_gui.models.spacewire_status import SpaceWireStatus


class RosSpaceWireBackend(SpaceWireBackend):
    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self._cached_status = SpaceWireStatus()
        self._connect_op_pending = False
        self._shutting_down = False

        self._thread = QThread()
        self._worker = RosWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.setup)
        self._worker.finished.connect(self._thread.quit)

        self._worker.status_ready.connect(self._on_status_ready)
        self._worker.image_ready.connect(self._on_image_ready)
        self._worker.housekeeping_ready.connect(self._on_housekeeping_ready)
        self._worker.operation_finished.connect(self._on_operation_finished)
        self._worker.worker_log.connect(self.log_message.emit)
        self._worker.worker_error.connect(self.connection_error.emit)

        self._thread.start()

    @property
    def backend_name(self) -> str:
        return "ROS"

    @property
    def is_busy(self) -> bool:
        return self._connect_op_pending

    def get_status(self) -> SpaceWireStatus:
        return self._cached_status.copy()

    def connect_spacewire(self) -> None:
        if self._shutting_down or self._connect_op_pending:
            return
        if self._cached_status.running or self._cached_status.connecting:
            return

        self._connect_op_pending = True
        self._worker.connect_requested.emit()
        self.log_message.emit("Connect requested")

    def disconnect_spacewire(self) -> None:
        if self._shutting_down or self._connect_op_pending:
            return
        if (
            not self._cached_status.started
            and not self._cached_status.running
            and not self._cached_status.connecting
        ):
            return

        self._connect_op_pending = True
        self._worker.disconnect_requested.emit()
        self.log_message.emit("Disconnect requested")

    def request_image(self, pattern: int) -> None:
        if self._shutting_down:
            return
        if not self._cached_status.image_requests_available():
            self.connection_error.emit("Image request rejected: link not running")
            return

        label = PATTERN_LABELS.get(pattern, f"Pattern {pattern}")
        self.log_message.emit(f"{label} image requested")
        self._worker.capture_requested.emit(pattern)

    def request_housekeeping(self) -> None:
        if self._shutting_down:
            return
        if not self._cached_status.image_requests_available():
            message = "Housekeeping request rejected: link not running"
            self.connection_error.emit(message)
            self.housekeeping_request_finished.emit(False, message)
            return

        self.log_message.emit("Housekeeping requested")
        self._worker.housekeeping_requested.emit()

    def set_pattern(self, pattern: int) -> None:
        if self._shutting_down:
            return
        self._worker.pattern_set_requested.emit(pattern)

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True

        if not self._thread.isRunning():
            return

        self._worker.shutdown_requested.emit()
        if not self._thread.wait(THREAD_JOIN_TIMEOUT_MS):
            self.log_message.emit("Warning: ROS worker thread did not stop cleanly")

    def _on_status_ready(self, status: SpaceWireStatus) -> None:
        self._cached_status = status
        self.status_updated.emit(status.copy())

    def _on_image_ready(self, image: QImage) -> None:
        self.image_received.emit(image)
        self.log_message.emit(f"Image received: {image.width()}x{image.height()}")

    def _on_housekeeping_ready(self, snapshot: object) -> None:
        self.housekeeping_updated.emit(snapshot)

    def _on_operation_finished(self, operation: str, success: bool, message: str) -> None:
        if operation in {"connect", "disconnect"}:
            self._connect_op_pending = False
            self.busy_changed.emit()
            if success and operation == "disconnect":
                self.log_message.emit("SpaceWire disconnected")
        elif operation == "housekeeping":
            self.housekeeping_request_finished.emit(success, message)
