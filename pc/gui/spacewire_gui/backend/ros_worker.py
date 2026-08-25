"""ROS worker running rclpy on a dedicated QThread."""

from __future__ import annotations

from typing import Any

import rclpy
from diagnostic_msgs.msg import DiagnosticArray
from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger

from spacewire_gui.backend.ros_constants import (
    CAMERA_IMAGE_TOPIC,
    CONNECT_SERVICE,
    DIAGNOSTICS_TOPIC,
    DIAGNOSTIC_STATUS_NAME,
    DISCONNECT_SERVICE,
    GATEWAY_NODE,
    GET_HOUSEKEEPING_SERVICE,
    GUI_NODE_NAME,
    HOUSEKEEPING_TIMEOUT_MS,
    HOUSEKEEPING_TOPIC,
    IMAGE_REQUEST_TIMEOUT_MS,
    PATTERN_PARAMETER,
    REQUEST_IMAGE_SERVICE,
    SPIN_INTERVAL_MS,
)
from spacewire_gui.backend.ros_image import ros_image_to_qimage
from spacewire_gui.models.diagnostics_mapping import merge_key_values
from spacewire_gui.models.housekeeping_mapping import parse_diagnostic_array
from spacewire_gui.models.image_patterns import ALL_PATTERNS, PATTERN_LABELS
from spacewire_gui.models.spacewire_status import SpaceWireStatus


class RosWorker(QObject):
    status_ready = Signal(object)
    image_ready = Signal(object)
    housekeeping_ready = Signal(object)
    operation_finished = Signal(str, bool, str)
    worker_log = Signal(str)
    worker_error = Signal(str)
    finished = Signal()

    connect_requested = Signal()
    disconnect_requested = Signal()
    pattern_set_requested = Signal(int)
    capture_requested = Signal(int)
    housekeeping_requested = Signal()
    shutdown_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._node: Node | None = None
        self._executor: SingleThreadedExecutor | None = None
        self._spin_timer: QTimer | None = None
        self._image_timeout_timer: QTimer | None = None
        self._housekeeping_timeout_timer: QTimer | None = None
        self._param_client: AsyncParameterClient | None = None
        self._connect_client: Any = None
        self._disconnect_client: Any = None
        self._request_image_client: Any = None
        self._housekeeping_client: Any = None
        self._image_pending = False
        self._housekeeping_pending = False
        self._selected_pattern: int | None = None
        self._diagnostic_status = SpaceWireStatus()
        self._missing_diag_logged = False
        self._rclpy_initialized = False

        self.connect_requested.connect(self._on_connect, Qt.ConnectionType.QueuedConnection)
        self.disconnect_requested.connect(
            self._on_disconnect, Qt.ConnectionType.QueuedConnection
        )
        self.pattern_set_requested.connect(
            self._on_pattern_set_requested, Qt.ConnectionType.QueuedConnection
        )
        self.capture_requested.connect(
            self._on_capture_requested, Qt.ConnectionType.QueuedConnection
        )
        self.housekeeping_requested.connect(
            self._on_housekeeping_requested, Qt.ConnectionType.QueuedConnection
        )
        self.shutdown_requested.connect(self.teardown, Qt.ConnectionType.QueuedConnection)

    @Slot()
    def setup(self) -> None:
        if self._node is not None:
            return

        rclpy.init()
        self._rclpy_initialized = True

        self._node = Node(GUI_NODE_NAME)
        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self._node)

        self._param_client = AsyncParameterClient(self._node, remote_node_name=GATEWAY_NODE)
        self._connect_client = self._node.create_client(Trigger, CONNECT_SERVICE)
        self._disconnect_client = self._node.create_client(Trigger, DISCONNECT_SERVICE)
        self._request_image_client = self._node.create_client(Trigger, REQUEST_IMAGE_SERVICE)
        self._housekeeping_client = self._node.create_client(
            Trigger, GET_HOUSEKEEPING_SERVICE
        )

        self._node.create_subscription(
            DiagnosticArray,
            DIAGNOSTICS_TOPIC,
            self._on_diagnostics,
            10,
        )
        self._node.create_subscription(
            Image,
            CAMERA_IMAGE_TOPIC,
            self._on_image,
            10,
        )
        self._node.create_subscription(
            DiagnosticArray,
            HOUSEKEEPING_TOPIC,
            self._on_housekeeping,
            10,
        )

        self._spin_timer = QTimer(self)
        self._spin_timer.timeout.connect(self._spin_once)
        self._spin_timer.start(SPIN_INTERVAL_MS)

        self._image_timeout_timer = QTimer(self)
        self._image_timeout_timer.setSingleShot(True)
        self._image_timeout_timer.timeout.connect(self._on_image_timeout)

        self._housekeeping_timeout_timer = QTimer(self)
        self._housekeeping_timeout_timer.setSingleShot(True)
        self._housekeeping_timeout_timer.timeout.connect(self._on_housekeeping_timeout)

        self.worker_log.emit("ROS worker started")

    @Slot()
    def teardown(self) -> None:
        if self._spin_timer is not None:
            self._spin_timer.stop()
            self._spin_timer = None

        if self._image_timeout_timer is not None:
            self._image_timeout_timer.stop()
            self._image_timeout_timer = None

        if self._housekeeping_timeout_timer is not None:
            self._housekeeping_timeout_timer.stop()
            self._housekeeping_timeout_timer = None

        if self._executor is not None and self._node is not None:
            self._executor.remove_node(self._node)

        if self._node is not None:
            self._node.destroy_node()
            self._node = None

        self._executor = None
        self._param_client = None
        self._connect_client = None
        self._disconnect_client = None
        self._request_image_client = None
        self._housekeeping_client = None
        self._image_pending = False
        self._housekeeping_pending = False
        self._selected_pattern = None
        self._diagnostic_status = SpaceWireStatus()

        if self._rclpy_initialized and rclpy.ok():
            rclpy.shutdown()
        self._rclpy_initialized = False

        self.finished.emit()

    def _spin_once(self) -> None:
        if self._executor is not None:
            self._executor.spin_once(timeout_sec=0)

    def _on_diagnostics(self, msg: DiagnosticArray) -> None:
        for status in msg.status:
            if status.name == DIAGNOSTIC_STATUS_NAME:
                data = {kv.key: kv.value for kv in status.values}
                self._diagnostic_status = merge_key_values(self._diagnostic_status, data)
                self.status_ready.emit(self._diagnostic_status.copy())
                return

        if not self._missing_diag_logged:
            self._missing_diag_logged = True
            self.worker_log.emit(
                f'No "{DIAGNOSTIC_STATUS_NAME}" entry in {DIAGNOSTICS_TOPIC}'
            )

    def _on_image(self, msg: Image) -> None:
        try:
            image = ros_image_to_qimage(msg)
        except ValueError as exc:
            self._clear_image_pending()
            self.worker_error.emit(str(exc))
            return

        self._clear_image_pending()
        self.image_ready.emit(image)

    def _on_housekeeping(self, msg: DiagnosticArray) -> None:
        snapshot = parse_diagnostic_array(msg)
        self.housekeeping_ready.emit(snapshot)

    def _on_image_timeout(self) -> None:
        if not self._image_pending:
            return
        self._clear_image_pending()
        self.worker_error.emit("Image request timed out")

    def _clear_image_pending(self) -> None:
        self._image_pending = False
        if self._image_timeout_timer is not None:
            self._image_timeout_timer.stop()

    def _clear_housekeeping_pending(self) -> None:
        self._housekeeping_pending = False
        if self._housekeeping_timeout_timer is not None:
            self._housekeeping_timeout_timer.stop()

    @Slot()
    def _on_connect(self) -> None:
        self._call_trigger_service(
            self._connect_client,
            CONNECT_SERVICE,
            "connect",
            "Connect requested",
        )

    @Slot()
    def _on_disconnect(self) -> None:
        self._call_trigger_service(
            self._disconnect_client,
            DISCONNECT_SERVICE,
            "disconnect",
            "Disconnect requested",
        )

    @Slot(int)
    def _on_pattern_set_requested(self, pattern: int) -> None:
        if pattern not in ALL_PATTERNS:
            self.worker_error.emit(f"Invalid pattern: {pattern}")
            return
        if self._param_client is None:
            self.worker_error.emit("ROS parameter client is not ready")
            return

        self._selected_pattern = pattern
        future = self._param_client.set_parameters(
            [Parameter(PATTERN_PARAMETER, Parameter.Type.INTEGER, pattern)]
        )
        future.add_done_callback(
            lambda completed_future: self._on_pattern_only_set_done(completed_future, pattern)
        )

    def _set_parameters_results(self, future: Any) -> tuple[list[Any] | None, str | None]:
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001 - surface ROS failures to GUI log
            return None, f"Failed to set pattern parameter: {exc}"

        if response is None:
            return None, "Failed to set pattern parameter: empty response"

        results = getattr(response, "results", None)
        if not results:
            return None, "Failed to set pattern parameter: no results returned"

        failed = [result for result in results if not result.successful]
        if failed:
            reasons = ", ".join(result.reason for result in failed)
            return None, f"Failed to set pattern parameter: {reasons}"

        return list(results), None

    def _on_pattern_only_set_done(self, future: Any, pattern: int) -> None:
        try:
            label = PATTERN_LABELS.get(pattern, f"Pattern {pattern}")
            _, error = self._set_parameters_results(future)
            if error is not None:
                self.worker_error.emit(error)
                return

            self._selected_pattern = pattern
            self.worker_log.emit(f"Pattern set: {label}")
        except Exception as exc:  # noqa: BLE001 - keep executor callbacks safe
            self.worker_error.emit(f"Failed to set pattern parameter: {exc}")

    @Slot(int)
    def _on_capture_requested(self, pattern: int) -> None:
        if pattern not in ALL_PATTERNS:
            self.worker_error.emit(f"Invalid pattern: {pattern}")
            return
        if self._image_pending:
            return
        if self._housekeeping_pending:
            self.worker_error.emit(
                "Cannot request an image while housekeeping is in progress"
            )
            return
        if self._param_client is None:
            self.worker_error.emit("ROS parameter client is not ready")
            return

        self._selected_pattern = pattern
        self._image_pending = True

        future = self._param_client.set_parameters(
            [Parameter(PATTERN_PARAMETER, Parameter.Type.INTEGER, pattern)]
        )
        future.add_done_callback(
            lambda completed_future: self._on_pattern_set_before_capture(
                completed_future, pattern
            )
        )

    def _on_pattern_set_before_capture(self, future: Any, pattern: int) -> None:
        try:
            if not self._image_pending:
                return

            _, error = self._set_parameters_results(future)
            if error is not None:
                self._clear_image_pending()
                self.worker_error.emit(error)
                return

            self._selected_pattern = pattern
            self._call_request_image_service(pattern)
        except Exception as exc:  # noqa: BLE001 - keep executor callbacks safe
            self._clear_image_pending()
            self.worker_error.emit(f"Failed to set pattern parameter: {exc}")

    def _call_request_image_service(self, pattern: int) -> None:
        if self._request_image_client is None:
            self._clear_image_pending()
            self.worker_error.emit("Image request client is not ready")
            return

        if not self._request_image_client.wait_for_service(timeout_sec=1.0):
            self._clear_image_pending()
            self.worker_error.emit(f"Service unavailable: {REQUEST_IMAGE_SERVICE}")
            return

        future = self._request_image_client.call_async(Trigger.Request())
        future.add_done_callback(
            lambda completed_future: self._on_request_image_done(completed_future, pattern)
        )

    def _on_request_image_done(self, future: Any, pattern: int) -> None:
        if not self._image_pending:
            return

        label = PATTERN_LABELS.get(pattern, f"Pattern {pattern}")
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001 - surface ROS failures to GUI log
            self._clear_image_pending()
            message = f"Image request service error: {exc}"
            self.worker_error.emit(message)
            return

        if not response.success:
            message = response.message or f"{label} image request rejected"
            self._clear_image_pending()
            self.worker_error.emit(message)
            return

        if self._image_timeout_timer is not None:
            self._image_timeout_timer.start(IMAGE_REQUEST_TIMEOUT_MS)

    @Slot()
    def _on_housekeeping_requested(self) -> None:
        if self._housekeeping_pending:
            return
        if self._image_pending:
            message = "Cannot request housekeeping while an image request is active"
            self.operation_finished.emit("housekeeping", False, message)
            self.worker_error.emit(message)
            return
        if self._housekeeping_client is None:
            message = f"{GET_HOUSEKEEPING_SERVICE} client is not ready"
            self.operation_finished.emit("housekeeping", False, message)
            self.worker_error.emit(message)
            return

        if not self._housekeeping_client.wait_for_service(timeout_sec=1.0):
            message = f"Service unavailable: {GET_HOUSEKEEPING_SERVICE}"
            self.operation_finished.emit("housekeeping", False, message)
            self.worker_error.emit(message)
            return

        self._housekeeping_pending = True
        future = self._housekeeping_client.call_async(Trigger.Request())
        future.add_done_callback(self._on_housekeeping_done)
        if self._housekeeping_timeout_timer is not None:
            self._housekeeping_timeout_timer.start(HOUSEKEEPING_TIMEOUT_MS)

    def _on_housekeeping_done(self, future: Any) -> None:
        if not self._housekeeping_pending:
            return

        self._clear_housekeeping_pending()
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001 - surface ROS failures to GUI log
            message = f"{GET_HOUSEKEEPING_SERVICE} error: {exc}"
            self.operation_finished.emit("housekeeping", False, message)
            self.worker_error.emit(message)
            return

        message = response.message or (
            "Housekeeping succeeded" if response.success else "Housekeeping failed"
        )
        if response.success:
            self.worker_log.emit(message)
        else:
            self.worker_error.emit(message)
        self.operation_finished.emit("housekeeping", response.success, message)

    def _on_housekeeping_timeout(self) -> None:
        if not self._housekeeping_pending:
            return
        self._clear_housekeeping_pending()
        message = "Housekeeping request timed out"
        self.operation_finished.emit("housekeeping", False, message)
        self.worker_error.emit(message)

    def _call_trigger_service(
        self,
        client: Any,
        service_name: str,
        operation: str,
        log_message: str,
    ) -> None:
        if client is None:
            self.operation_finished.emit(operation, False, f"{service_name} client not ready")
            self.worker_error.emit(f"{service_name} client is not ready")
            return

        if not client.wait_for_service(timeout_sec=1.0):
            message = f"Service unavailable: {service_name}"
            self.operation_finished.emit(operation, False, message)
            self.worker_error.emit(message)
            return

        future = client.call_async(Trigger.Request())
        future.add_done_callback(
            lambda completed_future: self._on_trigger_done(
                completed_future, operation, service_name
            )
        )

    def _on_trigger_done(self, future: Any, operation: str, service_name: str) -> None:
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001 - surface ROS failures to GUI log
            message = f"{service_name} error: {exc}"
            self.operation_finished.emit(operation, False, message)
            self.worker_error.emit(message)
            return

        message = response.message or (
            f"{operation.capitalize()} succeeded"
            if response.success
            else f"{operation.capitalize()} failed"
        )
        if response.success:
            self.worker_log.emit(message)
        else:
            self.worker_error.emit(message)
        self.operation_finished.emit(operation, response.success, message)
