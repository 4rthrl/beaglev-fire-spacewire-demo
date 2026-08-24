"""Backend implementations for SpaceWire Camera Control.

RosSpaceWireBackend is imported lazily from ``spacewire_gui.backend.ros_backend``
so the application can run without ROS installed.
"""

from spacewire_gui.backend.base import SpaceWireBackend
from spacewire_gui.backend.mock_backend import MockSpaceWireBackend

__all__ = ["MockSpaceWireBackend", "SpaceWireBackend"]
