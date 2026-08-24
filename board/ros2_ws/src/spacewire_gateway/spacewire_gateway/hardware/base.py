"""Pure-Python hardware abstraction for SpaceWire gateway backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SpaceWireStatus:
    started: bool = False
    connecting: bool = False
    running: bool = False
    tx_ready: bool = False
    tx_half_full: bool = False
    rx_valid: bool = False
    rx_half_full: bool = False
    disconnect_error: bool = False
    parity_error: bool = False
    escape_error: bool = False
    credit_error: bool = False
    tx_divider: int = 0
    control_raw: int = 0
    status_raw: int = 0
    errors_raw: int = 0
    core_id: int = 0


@dataclass
class ReceivedImage:
    width: int
    height: int
    encoding: str
    step: int
    data: bytes


class SpaceWireHardware(ABC):

    @abstractmethod
    def connect(self) -> tuple[bool, str]:
        """Start or confirm the SpaceWire link."""

    @abstractmethod
    def disconnect(self) -> tuple[bool, str]:
        """Stop the SpaceWire link."""

    @abstractmethod
    def get_status(self) -> SpaceWireStatus:
        """Return a fresh snapshot of the current hardware status."""

    @abstractmethod
    def request_image(self, pattern: int) -> tuple[bool, str]:
        """Arm an image request without blocking until data arrives."""

    @abstractmethod
    def poll_image(self) -> ReceivedImage | None:
        """Return a completed image once available, otherwise None."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release hardware resources."""
