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
class CameraHousekeeping:
    # Identification
    device_id: int
    destination_address: int
    protocol_id: int
    protocol_version: int
    fw_version: int
    register_map_version: int
    capabilities: int

    # Camera state
    bist_status: int
    operating_mode: int
    image_source: int
    pattern: int
    bayer: int
    camera_status: int
    last_error: int

    # Image configuration
    integration_time: int
    lup_config: int
    image_corrections: int
    nuc_lut_version: int
    bp_lut_version: int
    test_pattern_a_version: int
    test_pattern_b_version: int
    image_size: int

    # Counters
    tc_counter: int
    last_tc_id: int
    last_tc_status: int
    frame_counter: int
    abort_counter: int
    command_error_counter: int
    uptime_seconds: int

    # Monitors
    monitor_valid: int
    temp_detector: int
    vdd20_voltage: int
    core_1v2_current: int
    core_1v2_voltage: int
    io_3v3_current: int
    io_3v3_voltage: int
    input_5v_current: int
    temp_fpga: int
    temp_power: int

    # SpaceWire diagnostics
    spw_rx_packet_counter: int
    spw_tx_packet_counter: int
    spw_error_counter: int
    last_spw_error: int


    # ------------------------------------------------------------------
    # Identification / versions
    # ------------------------------------------------------------------
    @staticmethod
    def _version_parts(value: int) -> tuple[int, int, int]:
        return (
            (value >> 16) & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF,
        )

    @staticmethod
    def _version_text(value: int) -> str:
        major, minor, patch = CameraHousekeeping._version_parts(value)
        return f'{major}.{minor}.{patch}'

    @property
    def destination_address_value(self) -> int:
        return self.destination_address & 0xFF

    @property
    def protocol_id_value(self) -> int:
        return self.protocol_id & 0xFF

    @property
    def protocol_version_text(self) -> str:
        return self._version_text(self.protocol_version)

    @property
    def fw_version_text(self) -> str:
        return self._version_text(self.fw_version)

    @property
    def register_map_version_text(self) -> str:
        return self._version_text(self.register_map_version)

    # ------------------------------------------------------------------
    # Capabilities [7:0]
    # ------------------------------------------------------------------
    @property
    def capability_generated_patterns(self) -> bool:
        return bool(self.capabilities & (1 << 0))

    @property
    def capability_bist(self) -> bool:
        return bool(self.capabilities & (1 << 1))

    @property
    def capability_monitor_values(self) -> bool:
        return bool(self.capabilities & (1 << 2))

    @property
    def capability_integration_time(self) -> bool:
        return bool(self.capabilities & (1 << 3))

    @property
    def capability_image_corrections(self) -> bool:
        return bool(self.capabilities & (1 << 4))

    @property
    def capability_stored_patterns(self) -> bool:
        return bool(self.capabilities & (1 << 5))

    @property
    def capability_logical_address(self) -> bool:
        return bool(self.capabilities & (1 << 6))

    @property
    def capability_bayer(self) -> bool:
        return bool(self.capabilities & (1 << 7))

    # ------------------------------------------------------------------
    # BIST
    # [15:8] error code, [7] failed, [6:0] test ID
    # ------------------------------------------------------------------
    @property
    def bist_test_id(self) -> int:
        return self.bist_status & 0x7F

    @property
    def bist_failed(self) -> bool:
        return bool((self.bist_status >> 7) & 0x1)

    @property
    def bist_error_code(self) -> int:
        return (self.bist_status >> 8) & 0xFF

    # ------------------------------------------------------------------
    # Operating mode [3:0]
    # ------------------------------------------------------------------
    @property
    def operating_mode_code(self) -> int:
        return self.operating_mode & 0xF

    @property
    def operating_mode_name(self) -> str:
        names = {
            0: 'Starting Up',
            1: 'StandBy',
            2: 'Service',
            3: 'Multiple Imaging',
            4: 'Single Imaging',
            5: 'Maintenance',
        }
        return names.get(
            self.operating_mode_code,
            f'Unknown ({self.operating_mode_code})',
        )

    # ------------------------------------------------------------------
    # Image source [3:0]
    # ------------------------------------------------------------------
    @property
    def image_source_code(self) -> int:
        return self.image_source & 0xF

    @property
    def image_source_name(self) -> str:
        names = {
            0: 'None',
            1: 'Image Sensor',
            2: 'Stored Patterns',
            3: 'Generated Patterns',
        }
        return names.get(
            self.image_source_code,
            f'Unknown ({self.image_source_code})',
        )

    @property
    def pattern_select(self) -> int:
        return self.pattern & 0x7

    @property
    def bayer_pattern(self) -> int:
        return self.bayer & 0x3

    # ------------------------------------------------------------------
    # Camera status
    # [2] error, [1] BIST running, [0] frame active
    # ------------------------------------------------------------------
    @property
    def frame_active(self) -> bool:
        return bool(self.camera_status & (1 << 0))

    @property
    def bist_running(self) -> bool:
        return bool(self.camera_status & (1 << 1))

    @property
    def error_present(self) -> bool:
        return bool(self.camera_status & (1 << 2))

    @property
    def last_error_code(self) -> int:
        return self.last_error & 0xFFFF

    # ------------------------------------------------------------------
    # LUP
    # [7] enable, [6:0] threshold
    # ------------------------------------------------------------------
    @property
    def lup_enabled(self) -> bool:
        return bool((self.lup_config >> 7) & 0x1)

    @property
    def lup_threshold(self) -> int:
        return self.lup_config & 0x7F

    # ------------------------------------------------------------------
    # Image corrections
    # [7:6] PLR, [5:4] corner, [3] binning,
    # [2] gain, [1] offset, [0] bad pixel
    # ------------------------------------------------------------------
    @property
    def correction_bad_pixel(self) -> bool:
        return bool(self.image_corrections & (1 << 0))

    @property
    def correction_offset(self) -> bool:
        return bool(self.image_corrections & (1 << 1))

    @property
    def correction_gain(self) -> bool:
        return bool(self.image_corrections & (1 << 2))

    @property
    def correction_binning(self) -> bool:
        return bool(self.image_corrections & (1 << 3))

    @property
    def correction_corner(self) -> int:
        return (self.image_corrections >> 4) & 0x3

    @property
    def correction_corner_name(self) -> str:
        names = {
            0: 'Upper Left',
            1: 'Upper Right',
            2: 'Lower Left',
            3: 'Lower Right',
        }
        return names[self.correction_corner]

    @property
    def correction_plr(self) -> int:
        return (self.image_corrections >> 6) & 0x3

    @property
    def nuc_lut_version_value(self) -> int:
        return self.nuc_lut_version & 0xFF

    @property
    def bp_lut_version_value(self) -> int:
        return self.bp_lut_version & 0xFF

    @property
    def test_pattern_a_version_value(self) -> int:
        return self.test_pattern_a_version & 0xFF

    @property
    def test_pattern_b_version_value(self) -> int:
        return self.test_pattern_b_version & 0xFF

    # ------------------------------------------------------------------
    # Image size
    # [31:16] height, [15:0] width
    # ------------------------------------------------------------------
    @property
    def image_height(self) -> int:
        return (self.image_size >> 16) & 0xFFFF

    @property
    def image_width(self) -> int:
        return self.image_size & 0xFFFF

    # ------------------------------------------------------------------
    # Last TC
    # ------------------------------------------------------------------
    @property
    def last_tc_id_value(self) -> int:
        return self.last_tc_id & 0xFF

    @property
    def tc_ack(self) -> bool:
        return bool(self.last_tc_status & (1 << 0))

    @property
    def tc_data_error(self) -> bool:
        return bool(self.last_tc_status & (1 << 1))

    @property
    def tc_id_error(self) -> bool:
        return bool(self.last_tc_status & (1 << 2))

    @property
    def tc_length_error(self) -> bool:
        return bool(self.last_tc_status & (1 << 3))

    @property
    def tc_crc_error(self) -> bool:
        return bool(self.last_tc_status & (1 << 4))

    # ------------------------------------------------------------------
    # Monitor validity bitmap [8:0]
    # ------------------------------------------------------------------
    @property
    def detector_temperature_valid(self) -> bool:
        return bool(self.monitor_valid & (1 << 0))

    @property
    def vdd20_voltage_valid(self) -> bool:
        return bool(self.monitor_valid & (1 << 1))

    @property
    def core_1v2_current_valid(self) -> bool:
        return bool(self.monitor_valid & (1 << 2))

    @property
    def core_1v2_voltage_valid(self) -> bool:
        return bool(self.monitor_valid & (1 << 3))

    @property
    def io_3v3_current_valid(self) -> bool:
        return bool(self.monitor_valid & (1 << 4))

    @property
    def io_3v3_voltage_valid(self) -> bool:
        return bool(self.monitor_valid & (1 << 5))

    @property
    def input_5v_current_valid(self) -> bool:
        return bool(self.monitor_valid & (1 << 6))

    @property
    def fpga_temperature_valid(self) -> bool:
        return bool(self.monitor_valid & (1 << 7))

    @property
    def power_temperature_valid(self) -> bool:
        return bool(self.monitor_valid & (1 << 8))

    @property
    def all_monitors_valid(self) -> bool:
        return (self.monitor_valid & 0x1FF) == 0x1FF

    @property
    def any_monitors_valid(self) -> bool:
        return bool(self.monitor_valid & 0x1FF)


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
    def get_housekeeping(
        self,
    ) -> tuple[bool, str, CameraHousekeeping | None]:
        """Request and return a decoded camera housekeeping snapshot."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release hardware resources."""
