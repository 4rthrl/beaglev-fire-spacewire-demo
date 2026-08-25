"""Human-readable formatting of a camera housekeeping snapshot.

The ROS gateway already decodes registers. This module formats those decoded
fields for the GUI and applies hardware-aware special cases (BIST not
implemented, invalid monitors, capability names).
"""

from __future__ import annotations

from spacewire_gui.models.housekeeping import (
    GROUP_COUNTERS,
    GROUP_IDENTIFICATION,
    GROUP_IMAGE_CONFIG,
    GROUP_MONITORS,
    GROUP_ORDER,
    GROUP_SPACEWIRE,
    GROUP_STATE,
    LEVEL_ERROR,
    HousekeepingSnapshot,
)
from spacewire_gui.models.image_patterns import PATTERN_LABELS

SEVERITY_INACTIVE = "inactive"
SEVERITY_ACTIVE = "active"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"

EMPTY = "—"
NOT_SUPPORTED = "Not supported"
UNAVAILABLE = "Unavailable"

_TRUTHY = frozenset({"1", "true", "yes", "on"})

CAPABILITY_KEYS: tuple[str, ...] = (
    "cap_generated_patterns",
    "cap_bist",
    "cap_monitor_values",
    "cap_integration_time",
    "cap_image_corrections",
    "cap_stored_patterns",
    "cap_logical_address",
    "cap_bayer",
)

FIELD_LABELS: dict[str, str] = {
    "device_id": "Camera ID",
    "destination_address": "Destination Address",
    "protocol_id": "Protocol ID",
    "protocol_version": "Protocol Version",
    "fw_version": "Firmware Version",
    "register_map_version": "Register Map Version",
    "capabilities_raw": "Capabilities",
    "cap_generated_patterns": "Generated Patterns",
    "cap_bist": "BIST",
    "cap_monitor_values": "Monitor Values",
    "cap_integration_time": "Integration Time",
    "cap_image_corrections": "Image Corrections",
    "cap_stored_patterns": "Stored Patterns",
    "cap_logical_address": "Logical Address",
    "cap_bayer": "Bayer",
    "operating_mode": "Operating Mode",
    "image_source": "Image Source",
    "pattern": "Current Pattern",
    "bayer_pattern": "Bayer Pattern",
    "frame_active": "Frame Active",
    "bist_running": "BIST Running",
    "error_present": "Error Present",
    "camera_status_raw": "Camera Status",
    "last_error_code": "Last Error Code",
    "bist_supported": "BIST Supported",
    "bist_test_id": "BIST Test ID",
    "bist_failed": "BIST Result",
    "bist_error_code": "BIST Error Code",
    "bist_status_raw": "BIST Status",
    "integration_time_us": "Integration Time",
    "lup_enabled": "LUP",
    "lup_threshold": "LUP Threshold",
    "lup_raw": "LUP Register",
    "correction_bad_pixel": "Bad Pixel",
    "correction_offset": "Offset",
    "correction_gain": "Gain",
    "correction_binning": "Binning",
    "correction_corner": "Corner",
    "correction_plr": "PLR",
    "image_corrections_raw": "Image Corrections",
    "nuc_lut_version": "NUC LUT Version",
    "bp_lut_version": "BP LUT Version",
    "test_pattern_a_version": "Test Pattern A Version",
    "test_pattern_b_version": "Test Pattern B Version",
    "image_size_raw": "Image Size",
    "tc_counter": "TC Counter",
    "last_tc_id": "Last TC ID",
    "tc_ack": "ACK",
    "tc_data_error": "Data Error",
    "tc_id_error": "ID Error",
    "tc_length_error": "Length Error",
    "tc_crc_error": "CRC Error",
    "last_tc_status_raw": "Last TC Status",
    "frame_counter": "Frame Counter",
    "abort_counter": "Abort Counter",
    "command_error_counter": "Command Error Counter",
    "uptime_seconds": "Uptime",
    "monitor_valid_raw": "Monitor Valid",
    "detector_temperature_raw": "Detector Temperature",
    "vdd20_voltage_raw": "VDD 2.0 V",
    "core_1v2_current_raw": "Core 1.2 V Current",
    "core_1v2_voltage_raw": "Core 1.2 V",
    "io_3v3_current_raw": "I/O 3.3 V Current",
    "io_3v3_voltage_raw": "I/O 3.3 V",
    "input_5v_current_raw": "Input 5 V Current",
    "fpga_temperature_raw": "FPGA Temperature",
    "power_temperature_raw": "Power Temperature",
    "rx_packet_counter": "RX Packet Counter",
    "tx_packet_counter": "TX Packet Counter",
    "error_counter": "Error Counter",
    "last_error": "Last SpaceWire Error",
}

GROUP_DISPLAY_KEYS: dict[str, tuple[str, ...]] = {
    GROUP_IDENTIFICATION: (
        "device_id",
        "destination_address",
        "protocol_id",
        "protocol_version",
        "fw_version",
        "register_map_version",
        "cap_generated_patterns",
        "cap_bist",
        "cap_monitor_values",
        "cap_integration_time",
        "cap_image_corrections",
        "cap_stored_patterns",
        "cap_logical_address",
        "cap_bayer",
        "capabilities_raw",
    ),
    GROUP_STATE: (
        "operating_mode",
        "image_source",
        "pattern",
        "bayer_pattern",
        "frame_active",
        "error_present",
        "camera_status_raw",
        "last_error_code",
        "bist_supported",
        "bist_running",
        "bist_test_id",
        "bist_failed",
        "bist_error_code",
        "bist_status_raw",
    ),
    GROUP_IMAGE_CONFIG: (
        "image_size_raw",
        "integration_time_us",
        "lup_enabled",
        "lup_threshold",
        "lup_raw",
        "correction_bad_pixel",
        "correction_offset",
        "correction_gain",
        "correction_binning",
        "correction_corner",
        "correction_plr",
        "image_corrections_raw",
        "nuc_lut_version",
        "bp_lut_version",
        "test_pattern_a_version",
        "test_pattern_b_version",
    ),
    GROUP_COUNTERS: (
        "tc_counter",
        "last_tc_id",
        "tc_ack",
        "tc_data_error",
        "tc_id_error",
        "tc_length_error",
        "tc_crc_error",
        "last_tc_status_raw",
        "frame_counter",
        "abort_counter",
        "command_error_counter",
        "uptime_seconds",
    ),
    GROUP_MONITORS: (
        "monitor_valid_raw",
        "detector_temperature_raw",
        "vdd20_voltage_raw",
        "core_1v2_current_raw",
        "core_1v2_voltage_raw",
        "io_3v3_current_raw",
        "io_3v3_voltage_raw",
        "input_5v_current_raw",
        "fpga_temperature_raw",
        "power_temperature_raw",
    ),
    GROUP_SPACEWIRE: (
        "rx_packet_counter",
        "tx_packet_counter",
        "error_counter",
        "last_error",
    ),
}

_BIST_RESULT_KEYS = frozenset(
    {
        "bist_running",
        "bist_failed",
        "bist_test_id",
        "bist_error_code",
    }
)

_MONITOR_VALID_KEYS: dict[str, str] = {
    "detector_temperature_raw": "detector_temperature_valid",
    "vdd20_voltage_raw": "vdd20_voltage_valid",
    "core_1v2_current_raw": "core_1v2_current_valid",
    "core_1v2_voltage_raw": "core_1v2_voltage_valid",
    "io_3v3_current_raw": "io_3v3_current_valid",
    "io_3v3_voltage_raw": "io_3v3_voltage_valid",
    "input_5v_current_raw": "input_5v_current_valid",
    "fpga_temperature_raw": "fpga_temperature_valid",
    "power_temperature_raw": "power_temperature_valid",
}

_YES_NO_KEYS = frozenset(
    {
        "frame_active",
        "error_present",
        "bist_supported",
        "tc_ack",
        "tc_data_error",
        "tc_id_error",
        "tc_length_error",
        "tc_crc_error",
        "correction_bad_pixel",
        "correction_offset",
        "correction_gain",
        "correction_binning",
        *CAPABILITY_KEYS,
    }
)

_ERROR_FLAG_KEYS = frozenset(
    {
        "error_present",
        "tc_data_error",
        "tc_id_error",
        "tc_length_error",
        "tc_crc_error",
    }
)

_STYLE_NORMAL = "normal"
_STYLE_ERROR = "error"
_STYLE_UNAVAILABLE = "unavailable"
_STYLE_MONO = "mono"


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in _TRUTHY


def field_label(key: str) -> str:
    return FIELD_LABELS.get(key, key.replace("_", " ").title())


def group_display_keys(group_id: str) -> tuple[str, ...]:
    return GROUP_DISPLAY_KEYS.get(group_id, ())


def iter_searchable_fields(
    snapshot: HousekeepingSnapshot,
) -> list[tuple[str, str, str]]:
    """Return (group_id, key, search text) for fields present in *snapshot*."""
    items: list[tuple[str, str, str]] = []
    for group_id in GROUP_ORDER:
        group = snapshot.group(group_id)
        if group is None:
            continue
        present = group.as_dict()
        for key in group_display_keys(group_id):
            if key not in present:
                if key != "image_size_raw":
                    continue
                if not (snapshot.get("image_width") or snapshot.get("image_height")):
                    continue
            items.append((group_id, key, f"{field_label(key)}  ({key})"))
    return items


def format_named_code(name: str, code: str) -> str:
    name = name.strip()
    code = code.strip()
    if not name and not code:
        return EMPTY
    if not code:
        return name
    if not name:
        return f"[{code}]"
    return f"{name} [{code}]"


def format_image_size(snapshot: HousekeepingSnapshot, *, include_raw: bool = True) -> str:
    width = snapshot.get("image_width").strip()
    height = snapshot.get("image_height").strip()
    raw = snapshot.get("image_size_raw").strip()
    if not width and not height:
        return raw or EMPTY
    text = f"{width} × {height}"
    if include_raw and raw:
        text += f" [{raw}]"
    return text


def _bist_supported(snapshot: HousekeepingSnapshot) -> bool:
    return _is_truthy(snapshot.get("bist_supported") or snapshot.get("cap_bist"))


def _capability_summary(snapshot: HousekeepingSnapshot) -> str:
    enabled = [
        field_label(key)
        for key in CAPABILITY_KEYS
        if _is_truthy(snapshot.get(key))
    ]
    if not enabled:
        raw = snapshot.get("capabilities_raw")
        return raw or EMPTY
    return ", ".join(enabled)


def format_field(snapshot: HousekeepingSnapshot, key: str) -> str:
    if snapshot.is_empty():
        return EMPTY

    if key == "operating_mode":
        return format_named_code(
            snapshot.get("operating_mode"),
            snapshot.get("operating_mode_code"),
        )
    if key == "image_source":
        return format_named_code(
            snapshot.get("image_source"),
            snapshot.get("image_source_code"),
        )
    if key == "correction_corner":
        return format_named_code(
            snapshot.get("correction_corner"),
            snapshot.get("correction_corner_code"),
        )
    if key == "pattern":
        raw = snapshot.get("pattern").strip()
        if not raw:
            return EMPTY
        try:
            code = int(raw, 0)
        except ValueError:
            return raw
        label = PATTERN_LABELS.get(code, f"Pattern {code}")
        return f"{label} [{code}]"
    if key == "image_size_raw":
        return format_image_size(snapshot, include_raw=True)
    if key == "lup_enabled":
        return "Enabled" if _is_truthy(snapshot.get(key)) else "Disabled"
    if key in _BIST_RESULT_KEYS and not _bist_supported(snapshot):
        return NOT_SUPPORTED
    if key == "bist_failed":
        return "Failed" if _is_truthy(snapshot.get(key)) else "Passed"
    if key in _MONITOR_VALID_KEYS:
        raw = snapshot.get(key) or "0"
        if not _is_truthy(snapshot.get(_MONITOR_VALID_KEYS[key])):
            return f"{UNAVAILABLE} [raw {raw}]"
        return raw
    if key in _YES_NO_KEYS:
        if snapshot.get(key) == "":
            return EMPTY
        return "Yes" if _is_truthy(snapshot.get(key)) else "No"
    if key == "uptime_seconds":
        value = snapshot.get(key)
        return EMPTY if value == "" else f"{value} s"
    if key == "integration_time_us":
        value = snapshot.get(key)
        return EMPTY if value == "" else f"{value} µs"

    value = snapshot.get(key)
    return value if value != "" else EMPTY


def field_style(snapshot: HousekeepingSnapshot, key: str) -> str:
    if snapshot.is_empty():
        return _STYLE_NORMAL
    if key in _BIST_RESULT_KEYS and not _bist_supported(snapshot):
        return _STYLE_UNAVAILABLE
    if key in _MONITOR_VALID_KEYS and not _is_truthy(
        snapshot.get(_MONITOR_VALID_KEYS[key])
    ):
        return _STYLE_UNAVAILABLE
    if key in _ERROR_FLAG_KEYS and _is_truthy(snapshot.get(key)):
        return _STYLE_ERROR
    if key == "bist_failed" and _bist_supported(snapshot) and _is_truthy(snapshot.get(key)):
        return _STYLE_ERROR
    if key == "error_counter":
        try:
            if int(snapshot.get(key) or "0", 0) != 0:
                return _STYLE_ERROR
        except ValueError:
            pass
    if key == "last_error":
        raw = snapshot.get(key).strip().lower()
        if raw not in {"", "0", "0x0", "0x00000000"}:
            return _STYLE_ERROR
    if key in {
        "device_id",
        "capabilities_raw",
        "camera_status_raw",
        "last_error_code",
        "bist_status_raw",
        "lup_raw",
        "image_corrections_raw",
        "last_tc_status_raw",
        "monitor_valid_raw",
        "last_error",
        "destination_address",
        "protocol_id",
        "bist_error_code",
    }:
        return _STYLE_MONO
    return _STYLE_NORMAL


def camera_error_state(snapshot: HousekeepingSnapshot) -> tuple[str, str]:
    if snapshot.is_empty():
        return SEVERITY_INACTIVE, EMPTY
    if _is_truthy(snapshot.get("error_present")):
        code = snapshot.get("last_error_code")
        text = "ERROR"
        if code:
            text = f"ERROR [{code}]"
        return SEVERITY_ERROR, text
    return SEVERITY_ACTIVE, "OK"


def monitor_availability_state(snapshot: HousekeepingSnapshot) -> tuple[str, str]:
    if snapshot.is_empty():
        return SEVERITY_INACTIVE, EMPTY
    valid_flags = [snapshot.get(key) for key in _MONITOR_VALID_KEYS.values()]
    if not valid_flags:
        return SEVERITY_WARNING, UNAVAILABLE
    any_valid = any(_is_truthy(flag) for flag in valid_flags)
    all_valid = all(_is_truthy(flag) for flag in valid_flags)
    if all_valid:
        return SEVERITY_ACTIVE, "Available"
    if any_valid:
        return SEVERITY_WARNING, "Partial"
    return SEVERITY_WARNING, UNAVAILABLE


def spacewire_error_state(snapshot: HousekeepingSnapshot) -> tuple[str, str]:
    if snapshot.is_empty():
        return SEVERITY_INACTIVE, EMPTY
    group = snapshot.group(GROUP_SPACEWIRE)
    if group is not None and group.level >= LEVEL_ERROR:
        last_error = snapshot.get("last_error")
        if last_error:
            return SEVERITY_ERROR, f"ERROR [{last_error}]"
        return SEVERITY_ERROR, "ERROR"
    try:
        error_count = int(snapshot.get("error_counter") or "0", 0)
    except ValueError:
        error_count = 0
    last_error = snapshot.get("last_error").strip().lower()
    has_error = error_count != 0 or last_error not in {"", "0", "0x0", "0x00000000"}
    if has_error:
        return SEVERITY_ERROR, "ERROR"
    return SEVERITY_ACTIVE, "OK"


def summary_camera_id(snapshot: HousekeepingSnapshot) -> str:
    return snapshot.get("device_id") or EMPTY


def summary_firmware(snapshot: HousekeepingSnapshot) -> str:
    return snapshot.get("fw_version") or EMPTY


def summary_operating_mode(snapshot: HousekeepingSnapshot) -> str:
    if snapshot.is_empty():
        return EMPTY
    return format_field(snapshot, "operating_mode")


def summary_image_source(snapshot: HousekeepingSnapshot) -> str:
    if snapshot.is_empty():
        return EMPTY
    return format_field(snapshot, "image_source")


def summary_pattern(snapshot: HousekeepingSnapshot) -> str:
    if snapshot.is_empty():
        return EMPTY
    return format_field(snapshot, "pattern")


def summary_image_size(snapshot: HousekeepingSnapshot) -> str:
    if snapshot.is_empty():
        return EMPTY
    return format_image_size(snapshot, include_raw=False)


def summary_tc_counter(snapshot: HousekeepingSnapshot) -> str:
    return snapshot.get("tc_counter") or EMPTY


def summary_frame_counter(snapshot: HousekeepingSnapshot) -> str:
    return snapshot.get("frame_counter") or EMPTY


def summary_capabilities(snapshot: HousekeepingSnapshot) -> str:
    if snapshot.is_empty():
        return EMPTY
    return _capability_summary(snapshot)
