"""Unit tests for camera housekeeping snapshot mapping and display formatting."""

from __future__ import annotations

import unittest

from spacewire_gui.models.housekeeping import (
    GROUP_IDENTIFICATION,
    GROUP_SPACEWIRE,
    GROUP_STATE,
    LEVEL_ERROR,
    LEVEL_OK,
    LEVEL_WARN,
    HousekeepingField,
    HousekeepingGroup,
    HousekeepingSnapshot,
)
from spacewire_gui.models.housekeeping_display import (
    NOT_SUPPORTED,
    UNAVAILABLE,
    SEVERITY_ACTIVE,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    camera_error_state,
    field_style,
    format_field,
    format_image_size,
    monitor_availability_state,
    spacewire_error_state,
    summary_capabilities,
    summary_image_size,
    summary_operating_mode,
)
from spacewire_gui.models.housekeeping_mapping import (
    _diagnostic_level_value,
    mock_housekeeping_snapshot,
    parse_diagnostic_array,
    snapshot_from_groups,
    snapshot_with_spacewire_error,
)


class _KeyValue:
    def __init__(self, key: str, value: str) -> None:
        self.key = key
        self.value = value


class _Status:
    def __init__(
        self,
        name: str,
        level: int,
        message: str,
        values: list[tuple[str, str]],
        hardware_id: str = "",
    ) -> None:
        self.name = name
        self.level = level
        self.message = message
        self.hardware_id = hardware_id
        self.values = [_KeyValue(key, value) for key, value in values]


class _Array:
    def __init__(self, statuses: list[_Status]) -> None:
        self.status = statuses


def _replace_field(snapshot: HousekeepingSnapshot, key: str, value: object) -> HousekeepingSnapshot:
    updated = snapshot.copy()
    for group_id, group in list(updated.groups.items()):
        fields = []
        changed = False
        for item in group.fields:
            if item.key == key:
                fields.append(HousekeepingField(key, str(value), group_id))
                changed = True
            else:
                fields.append(item)
        if changed:
            updated.groups[group_id] = HousekeepingGroup(
                group_id=group.group_id,
                level=group.level,
                message=group.message,
                fields=tuple(fields),
            )
    return updated


class HousekeepingMappingTests(unittest.TestCase):
    def test_parse_diagnostic_array_preserves_groups_and_values(self) -> None:
        msg = _Array(
            [
                _Status(
                    "Camera/Identification",
                    0,
                    "Camera identification and versions",
                    [("device_id", "0x43414D31"), ("fw_version", "1.0.0")],
                    hardware_id="camera-0x43414D31",
                ),
                _Status(
                    "Camera/State",
                    0,
                    "Camera state normal",
                    [("operating_mode", "StandBy"), ("operating_mode_code", "1")],
                ),
            ]
        )

        snapshot = parse_diagnostic_array(msg)

        self.assertEqual(snapshot.hardware_id, "camera-0x43414D31")
        self.assertEqual(snapshot.get("device_id"), "0x43414D31")
        self.assertEqual(snapshot.get("operating_mode"), "StandBy")
        self.assertEqual(snapshot.get("operating_mode_code"), "1")
        self.assertIsNotNone(snapshot.group(GROUP_IDENTIFICATION))
        self.assertIsNotNone(snapshot.group(GROUP_STATE))

    def test_diagnostic_level_value_accepts_ros_bytes(self) -> None:
        self.assertEqual(_diagnostic_level_value(b"\x00"), LEVEL_OK)
        self.assertEqual(_diagnostic_level_value(b"\x01"), LEVEL_WARN)
        self.assertEqual(_diagnostic_level_value(b"\x02"), LEVEL_ERROR)
        self.assertEqual(_diagnostic_level_value(bytearray(b"\x02")), LEVEL_ERROR)
        self.assertEqual(_diagnostic_level_value(0), LEVEL_OK)
        self.assertEqual(_diagnostic_level_value(2), LEVEL_ERROR)

    def test_parse_diagnostic_array_accepts_ros_byte_levels(self) -> None:
        msg = _Array(
            [
                _Status(
                    "Camera/Identification",
                    b"\x00",
                    "Camera identification and versions",
                    [("device_id", "0x43414D31")],
                ),
                _Status(
                    "Camera/Monitors",
                    b"\x01",
                    "Monitor values not valid",
                    [("monitor_valid_raw", "0x00000000")],
                ),
                _Status(
                    "Camera/SpaceWire",
                    b"\x02",
                    "Camera SpaceWire errors detected",
                    [("error_counter", "1"), ("last_error", "0x00000001")],
                ),
            ]
        )

        snapshot = parse_diagnostic_array(msg)

        identification = snapshot.group(GROUP_IDENTIFICATION)
        monitors = snapshot.group("Camera/Monitors")
        spacewire = snapshot.group(GROUP_SPACEWIRE)
        assert identification is not None
        assert monitors is not None
        assert spacewire is not None
        self.assertIsInstance(identification.level, int)
        self.assertEqual(identification.level, LEVEL_OK)
        self.assertEqual(monitors.level, LEVEL_WARN)
        self.assertEqual(spacewire.level, LEVEL_ERROR)

    def test_mock_snapshot_matches_gateway_mock_defaults(self) -> None:
        snapshot = mock_housekeeping_snapshot(pattern=3, tc_counter=4, frame_counter=2)

        self.assertEqual(snapshot.get("device_id"), "0x43414D31")
        self.assertEqual(snapshot.get("capabilities_raw"), "0x00000081")
        self.assertEqual(snapshot.get("cap_generated_patterns"), "True")
        self.assertEqual(snapshot.get("cap_bayer"), "True")
        self.assertEqual(snapshot.get("cap_bist"), "False")
        self.assertEqual(snapshot.get("operating_mode"), "StandBy")
        self.assertEqual(snapshot.get("image_source"), "Generated Patterns")
        self.assertEqual(snapshot.get("pattern"), "3")
        self.assertEqual(snapshot.get("image_width"), "64")
        self.assertEqual(snapshot.get("image_height"), "64")
        self.assertEqual(snapshot.get("tc_counter"), "4")
        self.assertEqual(snapshot.get("frame_counter"), "2")
        self.assertEqual(snapshot.get("monitor_valid_raw"), "0x00000000")
        self.assertEqual(snapshot.get("detector_temperature_valid"), "False")

    def test_snapshot_from_groups_stringifies_bools_like_ros(self) -> None:
        snapshot = snapshot_from_groups(
            (("Camera/State", 0, "ok", (("error_present", False), ("frame_active", True))),)
        )
        self.assertEqual(snapshot.get("error_present"), "False")
        self.assertEqual(snapshot.get("frame_active"), "True")


class HousekeepingDisplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = mock_housekeeping_snapshot(pattern=1, tc_counter=1, frame_counter=0)

    def test_operating_mode_includes_name_and_code(self) -> None:
        self.assertEqual(format_field(self.snapshot, "operating_mode"), "StandBy [1]")
        self.assertEqual(summary_operating_mode(self.snapshot), "StandBy [1]")

    def test_image_source_includes_name_and_code(self) -> None:
        self.assertEqual(
            format_field(self.snapshot, "image_source"),
            "Generated Patterns [3]",
        )

    def test_image_size_primary_and_raw(self) -> None:
        self.assertEqual(summary_image_size(self.snapshot), "64 × 64")
        self.assertEqual(format_image_size(self.snapshot), "64 × 64 [0x00400040]")
        self.assertEqual(format_field(self.snapshot, "image_size_raw"), "64 × 64 [0x00400040]")

    def test_capabilities_names_for_0x81(self) -> None:
        self.assertEqual(summary_capabilities(self.snapshot), "Generated Patterns, Bayer")
        self.assertEqual(format_field(self.snapshot, "cap_generated_patterns"), "Yes")
        self.assertEqual(format_field(self.snapshot, "cap_bist"), "No")
        self.assertEqual(format_field(self.snapshot, "cap_bayer"), "Yes")
        self.assertEqual(format_field(self.snapshot, "capabilities_raw"), "0x00000081")

    def test_bist_not_supported_is_not_passed(self) -> None:
        self.assertEqual(format_field(self.snapshot, "bist_failed"), NOT_SUPPORTED)
        self.assertEqual(format_field(self.snapshot, "bist_running"), NOT_SUPPORTED)
        self.assertEqual(format_field(self.snapshot, "bist_test_id"), NOT_SUPPORTED)
        self.assertEqual(format_field(self.snapshot, "bist_error_code"), NOT_SUPPORTED)
        self.assertNotIn("Passed", format_field(self.snapshot, "bist_failed"))
        self.assertEqual(field_style(self.snapshot, "bist_failed"), "unavailable")

    def test_bist_results_are_meaningful_only_when_supported(self) -> None:
        supported = _replace_field(self.snapshot, "bist_supported", True)
        supported = _replace_field(supported, "cap_bist", True)
        passed = _replace_field(supported, "bist_failed", False)
        failed = _replace_field(supported, "bist_failed", True)

        self.assertEqual(format_field(passed, "bist_failed"), "Passed")
        self.assertEqual(format_field(failed, "bist_failed"), "Failed")
        self.assertEqual(field_style(failed, "bist_failed"), "error")

    def test_monitors_invalid_are_unavailable_not_zero_measurements(self) -> None:
        formatted = format_field(self.snapshot, "detector_temperature_raw")
        self.assertTrue(formatted.startswith(UNAVAILABLE))
        self.assertIn("raw 0", formatted)
        self.assertEqual(field_style(self.snapshot, "detector_temperature_raw"), "unavailable")
        severity, text = monitor_availability_state(self.snapshot)
        self.assertEqual(severity, SEVERITY_WARNING)
        self.assertEqual(text, UNAVAILABLE)

    def test_lup_and_corrections(self) -> None:
        self.assertEqual(format_field(self.snapshot, "lup_enabled"), "Disabled")
        self.assertEqual(format_field(self.snapshot, "lup_threshold"), "0")
        self.assertEqual(format_field(self.snapshot, "correction_corner"), "Upper Left [0]")
        self.assertEqual(format_field(self.snapshot, "correction_bad_pixel"), "No")

    def test_last_tc_status_flags(self) -> None:
        self.assertEqual(format_field(self.snapshot, "tc_ack"), "No")
        self.assertEqual(format_field(self.snapshot, "tc_data_error"), "No")
        self.assertEqual(format_field(self.snapshot, "tc_id_error"), "No")
        self.assertEqual(format_field(self.snapshot, "tc_length_error"), "No")
        self.assertEqual(format_field(self.snapshot, "tc_crc_error"), "No")

        with_errors = _replace_field(self.snapshot, "tc_crc_error", True)
        self.assertEqual(format_field(with_errors, "tc_crc_error"), "Yes")
        self.assertEqual(field_style(with_errors, "tc_crc_error"), "error")

    def test_pattern_uses_human_label(self) -> None:
        self.assertEqual(
            format_field(self.snapshot, "pattern"),
            "Solid Red [1]",
        )

    def test_camera_and_spacewire_error_indicators(self) -> None:
        ok_severity, ok_text = camera_error_state(self.snapshot)
        self.assertEqual(ok_severity, SEVERITY_ACTIVE)
        self.assertEqual(ok_text, "OK")

        spw_ok, spw_ok_text = spacewire_error_state(self.snapshot)
        self.assertEqual(spw_ok, SEVERITY_ACTIVE)
        self.assertEqual(spw_ok_text, "OK")

        errored = snapshot_with_spacewire_error(self.snapshot)
        spw_err, spw_text = spacewire_error_state(errored)
        self.assertEqual(spw_err, SEVERITY_ERROR)
        self.assertIn("ERROR", spw_text)
        self.assertEqual(errored.group(GROUP_SPACEWIRE).level, 2)

    def test_empty_snapshot_uses_em_dash(self) -> None:
        empty = HousekeepingSnapshot()
        self.assertEqual(format_field(empty, "operating_mode"), "—")
        self.assertEqual(summary_image_size(empty), "—")
        self.assertEqual(monitor_availability_state(empty)[1], "—")


if __name__ == "__main__":
    unittest.main()
