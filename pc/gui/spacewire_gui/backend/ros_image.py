"""Convert sensor_msgs/Image messages to QImage for the GUI."""

from __future__ import annotations

from PySide6.QtGui import QImage


def ros_image_to_qimage(msg: object) -> QImage:
    """Convert a sensor_msgs/msg/Image to QImage.

    Supports rgb8 encoding. The returned image owns its pixel buffer.
    """
    encoding = getattr(msg, "encoding", "")
    width = int(getattr(msg, "width", 0))
    height = int(getattr(msg, "height", 0))
    step = int(getattr(msg, "step", 0))
    data = bytes(getattr(msg, "data", b""))

    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid image dimensions: {width}x{height}")

    if encoding == "rgb8":
        if step <= 0:
            step = width * 3
        image = QImage(data, width, height, step, QImage.Format.Format_RGB888)
        if image.isNull():
            raise ValueError("Failed to create QImage from rgb8 payload")
        return image.copy()

    raise ValueError(f"Unsupported image encoding: {encoding!r}")
