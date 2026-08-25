"""Parse camera housekeeping DiagnosticArray payloads into a GUI snapshot."""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from spacewire_gui.models.housekeeping import (
    GROUP_COUNTERS,
    GROUP_IDENTIFICATION,
    GROUP_IMAGE_CONFIG,
    GROUP_MONITORS,
    GROUP_SPACEWIRE,
    GROUP_STATE,
    LEVEL_ERROR,
    LEVEL_OK,
    LEVEL_WARN,
    HousekeepingField,
    HousekeepingGroup,
    HousekeepingSnapshot,
)

GroupValues = Sequence[tuple[str, Any]]


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def _diagnostic_level_value(level: Any) -> int:
    if isinstance(level, (bytes, bytearray, memoryview)):
        if len(level) != 1:
            raise ValueError(
                f"Expected one-byte DiagnosticStatus level, got {level!r}"
            )
        return level[0]
    return int(level)


def snapshot_from_groups(
    groups: Iterable[tuple[str, int, str, GroupValues]],
    hardware_id: str = "",
) -> HousekeepingSnapshot:
    """Build a snapshot from (name, level, message, key/value pairs) groups."""
    parsed: dict[str, HousekeepingGroup] = {}
    for name, level, message, values in groups:
        fields = tuple(
            HousekeepingField(key=key, value=_stringify(value), group_id=name)
            for key, value in values
        )
        parsed[name] = HousekeepingGroup(
            group_id=name,
            level=int(level),
            message=message,
            fields=fields,
        )
    return HousekeepingSnapshot(hardware_id=hardware_id, groups=parsed)


def parse_diagnostic_array(msg: Any) -> HousekeepingSnapshot:
    """Parse a diagnostic_msgs/DiagnosticArray (duck-typed) into a snapshot."""
    hardware_id = ""
    groups: list[tuple[str, int, str, list[tuple[str, str]]]] = []
    for status in getattr(msg, "status", ()):
        hardware_id = getattr(status, "hardware_id", "") or hardware_id
        values = [
            (kv.key, kv.value)
            for kv in getattr(status, "values", ())
        ]
        groups.append(
            (
                status.name,
                _diagnostic_level_value(status.level),
                status.message,
                values,
            )
        )
    return snapshot_from_groups(groups, hardware_id=hardware_id)


def mock_housekeeping_snapshot(
    *,
    pattern: int = 0,
    tc_counter: int = 1,
    frame_counter: int = 0,
    command_error_counter: int = 0,
) -> HousekeepingSnapshot:
    """Snapshot matching the gateway mock backend (capabilities 0x81, monitors invalid)."""
    hardware_id = "camera-0x43414D31"
    identification: GroupValues = (
        ("device_id", "0x43414D31"),
        ("destination_address", "0x00"),
        ("protocol_id", "0x01"),
        ("protocol_version", "1.0.0"),
        ("fw_version", "1.0.0"),
        ("register_map_version", "1.0.0"),
        ("capabilities_raw", "0x00000081"),
        ("cap_generated_patterns", True),
        ("cap_bist", False),
        ("cap_monitor_values", False),
        ("cap_integration_time", False),
        ("cap_image_corrections", False),
        ("cap_stored_patterns", False),
        ("cap_logical_address", False),
        ("cap_bayer", True),
    )
    state: GroupValues = (
        ("operating_mode", "StandBy"),
        ("operating_mode_code", 1),
        ("image_source", "Generated Patterns"),
        ("image_source_code", 3),
        ("pattern", pattern),
        ("bayer_pattern", 0),
        ("frame_active", False),
        ("bist_running", False),
        ("error_present", False),
        ("camera_status_raw", "0x00000000"),
        ("last_error_code", "0x0000"),
        ("bist_supported", False),
        ("bist_test_id", 0),
        ("bist_failed", False),
        ("bist_error_code", "0x00"),
        ("bist_status_raw", "0x00000000"),
    )
    configuration: GroupValues = (
        ("integration_time_us", 0),
        ("lup_enabled", False),
        ("lup_threshold", 0),
        ("lup_raw", "0x00000000"),
        ("correction_bad_pixel", False),
        ("correction_offset", False),
        ("correction_gain", False),
        ("correction_binning", False),
        ("correction_corner", "Upper Left"),
        ("correction_corner_code", 0),
        ("correction_plr", 0),
        ("image_corrections_raw", "0x00000000"),
        ("nuc_lut_version", 0),
        ("bp_lut_version", 0),
        ("test_pattern_a_version", 0),
        ("test_pattern_b_version", 0),
        ("image_width", 64),
        ("image_height", 64),
        ("image_size_raw", "0x00400040"),
    )
    counters: GroupValues = (
        ("tc_counter", tc_counter),
        ("last_tc_id", 0),
        ("tc_ack", False),
        ("tc_data_error", False),
        ("tc_id_error", False),
        ("tc_length_error", False),
        ("tc_crc_error", False),
        ("last_tc_status_raw", "0x00000000"),
        ("frame_counter", frame_counter),
        ("abort_counter", 0),
        ("command_error_counter", command_error_counter),
        ("uptime_seconds", 0),
    )
    monitors: GroupValues = (
        ("monitor_valid_raw", "0x00000000"),
        ("detector_temperature_valid", False),
        ("detector_temperature_raw", 0),
        ("vdd20_voltage_valid", False),
        ("vdd20_voltage_raw", 0),
        ("core_1v2_current_valid", False),
        ("core_1v2_current_raw", 0),
        ("core_1v2_voltage_valid", False),
        ("core_1v2_voltage_raw", 0),
        ("io_3v3_current_valid", False),
        ("io_3v3_current_raw", 0),
        ("io_3v3_voltage_valid", False),
        ("io_3v3_voltage_raw", 0),
        ("input_5v_current_valid", False),
        ("input_5v_current_raw", 0),
        ("fpga_temperature_valid", False),
        ("fpga_temperature_raw", 0),
        ("power_temperature_valid", False),
        ("power_temperature_raw", 0),
    )
    camera_spw: GroupValues = (
        ("rx_packet_counter", 0),
        ("tx_packet_counter", 0),
        ("error_counter", 0),
        ("last_error", "0x00000000"),
    )
    return snapshot_from_groups(
        (
            (GROUP_IDENTIFICATION, LEVEL_OK, "Camera identification and versions", identification),
            (GROUP_STATE, LEVEL_OK, "Camera state normal", state),
            (GROUP_IMAGE_CONFIG, LEVEL_OK, "Current image configuration", configuration),
            (GROUP_COUNTERS, LEVEL_OK, "Camera command and frame counters", counters),
            (GROUP_MONITORS, LEVEL_WARN, "Monitor values not valid", monitors),
            (GROUP_SPACEWIRE, LEVEL_OK, "Camera SpaceWire diagnostics clear", camera_spw),
        ),
        hardware_id=hardware_id,
    )


def snapshot_with_spacewire_error(
    base: HousekeepingSnapshot | None = None,
    *,
    error_counter: int = 1,
    last_error: str = "0x00000001",
) -> HousekeepingSnapshot:
    """Test helper: copy a snapshot and mark the camera SpaceWire group as error."""
    snapshot = (base or mock_housekeeping_snapshot()).copy()
    group = snapshot.group(GROUP_SPACEWIRE)
    if group is None:
        return snapshot
    fields = []
    for item in group.fields:
        if item.key == "error_counter":
            fields.append(HousekeepingField(item.key, str(error_counter), item.group_id))
        elif item.key == "last_error":
            fields.append(HousekeepingField(item.key, last_error, item.group_id))
        else:
            fields.append(item)
    snapshot.groups[GROUP_SPACEWIRE] = HousekeepingGroup(
        group_id=GROUP_SPACEWIRE,
        level=LEVEL_ERROR,
        message="Camera SpaceWire errors detected",
        fields=tuple(fields),
    )
    return snapshot
