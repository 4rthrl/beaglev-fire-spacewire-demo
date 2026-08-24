"""Application entry point."""

from __future__ import annotations

import argparse
import os
import sys

from PySide6.QtWidgets import QApplication

from spacewire_gui.backend.base import SpaceWireBackend
from spacewire_gui.backend.mock_backend import MockSpaceWireBackend
from spacewire_gui.gui.app_icon import load_app_icon
from spacewire_gui.gui.main_window import MainWindow
from spacewire_gui.gui.styles import load_stylesheet


def create_backend(name: str) -> SpaceWireBackend:
    if name == "ros":
        try:
            from spacewire_gui.backend.ros_backend import RosSpaceWireBackend
        except ImportError as exc:
            print(
                "ROS backend requires a sourced ROS 2 environment with rclpy installed.\n"
                "Example: source /opt/ros/jazzy/setup.bash",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        return RosSpaceWireBackend()
    if name != "mock":
        print(f"Unknown backend: {name!r}. Use 'mock' or 'ros'.", file=sys.stderr)
        raise SystemExit(2)
    return MockSpaceWireBackend()


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SpaceWire Camera Control GUI")
    parser.add_argument(
        "--backend",
        choices=("mock", "ros"),
        default=os.environ.get("SPACEWIRE_BACKEND", "mock"),
        help="Backend implementation (default: mock, or SPACEWIRE_BACKEND env var)",
    )
    args, _ros_args = parser.parse_known_args(argv)
    return args


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    app = QApplication([sys.argv[0]])
    app.setApplicationName("SpaceWire Camera Control")
    app.setWindowIcon(load_app_icon())
    app.setStyleSheet(load_stylesheet())

    backend = create_backend(args.backend)
    window = MainWindow(backend)
    window.show()

    backend.log_message.emit("Application started")

    exit_code = app.exec()
    backend.shutdown()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
