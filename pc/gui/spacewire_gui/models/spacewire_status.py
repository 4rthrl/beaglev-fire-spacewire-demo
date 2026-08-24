"""SpaceWire link status snapshot shared by mock and future ROS backends."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class LinkConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"


# Bit positions for errors_raw (mock simulation; align with hardware when known).
ERROR_BIT_DISCONNECT = 1 << 0
ERROR_BIT_PARITY = 1 << 1
ERROR_BIT_ESCAPE = 1 << 2
ERROR_BIT_CREDIT = 1 << 3


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

    def link_state(self) -> LinkConnectionState:
        if self.connecting:
            return LinkConnectionState.CONNECTING
        if self.running:
            return LinkConnectionState.CONNECTED
        return LinkConnectionState.DISCONNECTED

    def has_any_error(self) -> bool:
        return (
            self.disconnect_error
            or self.parity_error
            or self.escape_error
            or self.credit_error
        )

    def has_operator_errors(self) -> bool:
        """Errors shown in the operator link panel (excludes disconnect_error)."""
        return self.parity_error or self.escape_error or self.credit_error

    def image_requests_available(self) -> bool:
        return self.running and not self.connecting

    def summary_text(self) -> str:
        state = self.link_state()
        if state == LinkConnectionState.DISCONNECTED:
            return "Disconnected"
        if state == LinkConnectionState.CONNECTING:
            return "Connecting..."
        if self.has_any_error():
            return "Connected — Error detected"
        return "Connected"

    def compute_errors_raw(self) -> int:
        value = 0
        if self.disconnect_error:
            value |= ERROR_BIT_DISCONNECT
        if self.parity_error:
            value |= ERROR_BIT_PARITY
        if self.escape_error:
            value |= ERROR_BIT_ESCAPE
        if self.credit_error:
            value |= ERROR_BIT_CREDIT
        return value

    def sync_errors_raw(self) -> None:
        self.errors_raw = self.compute_errors_raw()

    @staticmethod
    def from_ros_json(data: dict[str, Any]) -> SpaceWireStatus:
        """Parse a legacy JSON status dict.

        Prefer :func:`spacewire_gui.models.diagnostics_mapping.parse_key_values`
        for current ``/diagnostics`` KeyValue payloads.
        """
        from spacewire_gui.models.diagnostics_mapping import parse_key_values

        return parse_key_values(data)

    def copy(self) -> SpaceWireStatus:
        return SpaceWireStatus(
            started=self.started,
            connecting=self.connecting,
            running=self.running,
            tx_ready=self.tx_ready,
            tx_half_full=self.tx_half_full,
            rx_valid=self.rx_valid,
            rx_half_full=self.rx_half_full,
            disconnect_error=self.disconnect_error,
            parity_error=self.parity_error,
            escape_error=self.escape_error,
            credit_error=self.credit_error,
            tx_divider=self.tx_divider,
            control_raw=self.control_raw,
            status_raw=self.status_raw,
            errors_raw=self.errors_raw,
            core_id=self.core_id,
        )
