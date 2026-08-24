"""Abstract backend interface for SpaceWire Camera Control.

The GUI depends only on this class. Backends emit Qt signals; the GUI connects
slots on the main thread and never blocks the event loop.

Future RosSpaceWireBackend design
---------------------------------
ROS / rclpy must run in a dedicated worker thread, not on the GUI thread.

Recommended layout::

    RosSpaceWireBackend(SpaceWireBackend)   # lives on GUI thread (signal relay)
        └── RosWorker(QObject)                # moved to QThread via moveToThread()
                └── rclpy node, subscriptions, service clients

- Use queued worker command signals for connect, disconnect, and image requests.
- Set the gateway ``pattern`` parameter via ``AsyncParameterClient`` before
  calling ``/camera/request_image``.
- RosWorker emits the same payload signals defined here; Qt automatically
  queues cross-thread delivery to GUI-thread slots.
- Create the executor polling ``QTimer`` inside ``RosWorker.setup()`` on the
  worker thread (parented to the worker).
- Call shutdown() from main() before QApplication exits: emit a queued
  shutdown signal to ``RosWorker.teardown()`` on the worker thread, wait for
  ``finished``, then join the ``QThread``.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from spacewire_gui.models.spacewire_status import SpaceWireStatus


class SpaceWireBackend(QObject):
    status_updated = Signal(object)  # SpaceWireStatus
    image_received = Signal(object)  # QImage
    log_message = Signal(str)
    connection_error = Signal(str)
    busy_changed = Signal()

    @property
    def backend_name(self) -> str:
        raise NotImplementedError

    @property
    def is_busy(self) -> bool:
        raise NotImplementedError

    def connect_spacewire(self) -> None:
        raise NotImplementedError

    def disconnect_spacewire(self) -> None:
        raise NotImplementedError

    def set_pattern(self, pattern: int) -> None:
        raise NotImplementedError

    def request_image(self, pattern: int) -> None:
        raise NotImplementedError

    def get_status(self) -> SpaceWireStatus:
        raise NotImplementedError

    def shutdown(self) -> None:
        """Release backend resources (override for threaded ROS backend)."""
