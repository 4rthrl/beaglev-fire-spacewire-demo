"""Map SpaceWire gateway diagnostic key/value pairs to SpaceWireStatus."""

from __future__ import annotations

from typing import Any

from spacewire_gui.models.spacewire_status import SpaceWireStatus

BOOL_FIELDS = (
    "started",
    "connecting",
    "running",
    "tx_ready",
    "tx_half_full",
    "rx_valid",
    "rx_half_full",
    "disconnect_error",
    "parity_error",
    "escape_error",
    "credit_error",
)

INT_FIELDS = (
    "tx_divider",
    "control_raw",
    "status_raw",
    "errors_raw",
    "core_id",
)

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if not text:
        return False
    return text in _TRUTHY


def _parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return 0
    return int(text, 0)


def parse_key_values(data: dict[str, Any]) -> SpaceWireStatus:
    """Build SpaceWireStatus from diagnostic KeyValue keys or a plain dict."""
    return merge_key_values(SpaceWireStatus(), data)


def merge_key_values(base: SpaceWireStatus, data: dict[str, Any]) -> SpaceWireStatus:
    """Apply only keys present in *data* onto a copy of *base*."""
    merged = base.copy()
    for field in BOOL_FIELDS:
        if field in data:
            setattr(merged, field, _parse_bool(data[field]))
    for field in INT_FIELDS:
        if field in data:
            setattr(merged, field, _parse_int(data[field]))
    return merged
