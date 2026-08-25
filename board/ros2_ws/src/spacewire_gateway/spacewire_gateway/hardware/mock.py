"""Mock SpaceWire hardware for development without FPGA."""

from __future__ import annotations

from dataclasses import replace

from spacewire_gateway.hardware.base import (
    CameraHousekeeping,
    ReceivedImage,
    SpaceWireHardware,
    SpaceWireStatus,
)

_IMAGE_WIDTH = 64
_IMAGE_HEIGHT = 64
_IMAGE_ENCODING = 'rgb8'
_IMAGE_STEP = _IMAGE_WIDTH * 3

_MIN_PATTERN = 0
_MAX_PATTERN = 7

_PATTERN_NAMES = {
    0: 'Color Boxes / Grid',
    1: 'Solid Red',
    2: 'Solid Green',
    3: 'Solid Blue',
    4: 'Vertical Color Bars',
    5: 'Horizontal Color Bars',
    6: 'Horizontal Black-to-White Gradient',
    7: 'Vertical Black-to-White Gradient',
}

_COLOR_BAR_PALETTE = (
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0),
    (0, 255, 255),
    (255, 0, 255),
    (255, 255, 255),
    (128, 128, 128),
)


def _color_box_rgb(x: int, y: int) -> tuple[int, int, int]:
    box_x = x // 8
    box_y = y // 8
    return (
        (box_x * 37 + box_y * 11) % 256,
        (box_y * 53 + box_x * 17) % 256,
        ((box_x + box_y) * 73) % 256,
    )


def _vertical_color_bars_rgb(x: int, y: int) -> tuple[int, int, int]:
    bar = min(x // 8, len(_COLOR_BAR_PALETTE) - 1)
    return _COLOR_BAR_PALETTE[bar]


def _horizontal_color_bars_rgb(x: int, y: int) -> tuple[int, int, int]:
    bar = min(y // 8, len(_COLOR_BAR_PALETTE) - 1)
    return _COLOR_BAR_PALETTE[bar]


def _horizontal_gradient_rgb(x: int, y: int) -> tuple[int, int, int]:
    level = int(255 * x / (_IMAGE_WIDTH - 1))
    return level, level, level


def _vertical_gradient_rgb(x: int, y: int) -> tuple[int, int, int]:
    level = int(255 * y / (_IMAGE_HEIGHT - 1))
    return level, level, level


def _pixel_rgb(pattern: int, x: int, y: int) -> tuple[int, int, int]:
    if pattern == 0:
        return _color_box_rgb(x, y)
    if pattern == 1:
        return 255, 0, 0
    if pattern == 2:
        return 0, 255, 0
    if pattern == 3:
        return 0, 0, 255
    if pattern == 4:
        return _vertical_color_bars_rgb(x, y)
    if pattern == 5:
        return _horizontal_color_bars_rgb(x, y)
    if pattern == 6:
        return _horizontal_gradient_rgb(x, y)
    return _vertical_gradient_rgb(x, y)


class MockSpaceWireHardware(SpaceWireHardware):

    def __init__(self) -> None:
        self._status = SpaceWireStatus(
            started=False,
            connecting=False,
            running=False,
            tx_ready=True,
            tx_half_full=False,
            rx_valid=False,
            rx_half_full=False,
            disconnect_error=False,
            parity_error=False,
            escape_error=False,
            credit_error=False,
            tx_divider=4,
            control_raw=0x00000000,
            status_raw=0x00000008,
            errors_raw=0x00000000,
            core_id=0x53505731,
        )
        self._pending_image: ReceivedImage | None = None
        self._current_pattern = 0
        self._tc_counter = 0
        self._frame_counter = 0
        self._command_error_counter = 0

    def connect(self) -> tuple[bool, str]:
        if self._status.running:
            return True, 'SpaceWire link already running'

        self._status = replace(
            self._status,
            started=True,
            connecting=False,
            running=True,
            tx_ready=True,
            control_raw=0x00000001,
            status_raw=0x0000000D,
        )
        return True, 'SpaceWire link connected'

    def disconnect(self) -> tuple[bool, str]:
        if not self._status.running and not self._status.started:
            return True, 'SpaceWire link already disconnected'

        self._pending_image = None
        self._status = replace(
            self._status,
            started=False,
            connecting=False,
            running=False,
            tx_ready=True,
            control_raw=0x00000004,
            status_raw=0x00000008,
        )
        return True, 'SpaceWire link disconnected'

    def get_status(self) -> SpaceWireStatus:
        return replace(self._status)

    def request_image(self, pattern: int) -> tuple[bool, str]:
        if not self._status.running:
            return False, 'SpaceWire link is not running'

        if not _MIN_PATTERN <= pattern <= _MAX_PATTERN:
            return False, f'Invalid pattern: {pattern}; expected 0..7'

        self._pending_image = self._generate_image(pattern)
        self._current_pattern = pattern
        self._tc_counter += 1
        self._frame_counter += 1

        pattern_name = _PATTERN_NAMES[pattern]
        return True, f'{pattern_name} image request accepted'

    def poll_image(self) -> ReceivedImage | None:
        if self._pending_image is None:
            return None

        image = self._pending_image
        self._pending_image = None
        return image

    def get_housekeeping(
        self,
    ) -> tuple[bool, str, CameraHousekeeping | None]:
        if not self._status.running:
            return False, 'SpaceWire link is not running', None

        # GET_HOUSEKEEPING itself is a valid telecommand.
        self._tc_counter += 1

        housekeeping = CameraHousekeeping(
            device_id=0x43414D31,
            destination_address=0x00000000,
            protocol_id=0x00000001,
            protocol_version=0x00010000,
            fw_version=0x00010000,
            register_map_version=0x00010000,
            capabilities=0x00000081,

            bist_status=0,
            operating_mode=1,
            image_source=3,
            pattern=self._current_pattern,
            bayer=0,
            camera_status=0,
            last_error=0,

            integration_time=0,
            lup_config=0,
            image_corrections=0,
            nuc_lut_version=0,
            bp_lut_version=0,
            test_pattern_a_version=0,
            test_pattern_b_version=0,
            image_size=0x00400040,

            tc_counter=self._tc_counter,
            last_tc_id=0,
            last_tc_status=0,
            frame_counter=self._frame_counter,
            abort_counter=0,
            command_error_counter=self._command_error_counter,
            uptime_seconds=0,

            monitor_valid=0,
            temp_detector=0,
            vdd20_voltage=0,
            core_1v2_current=0,
            core_1v2_voltage=0,
            io_3v3_current=0,
            io_3v3_voltage=0,
            input_5v_current=0,
            temp_fpga=0,
            temp_power=0,

            spw_rx_packet_counter=0,
            spw_tx_packet_counter=0,
            spw_error_counter=0,
            last_spw_error=0,
        )

        return True, 'Camera housekeeping received', housekeeping

    def shutdown(self) -> None:
        self._pending_image = None

    def _generate_image(self, pattern: int) -> ReceivedImage:
        data = bytearray()

        for y in range(_IMAGE_HEIGHT):
            for x in range(_IMAGE_WIDTH):
                r, g, b = _pixel_rgb(pattern, x, y)
                data.extend((r, g, b))

        return ReceivedImage(
            width=_IMAGE_WIDTH,
            height=_IMAGE_HEIGHT,
            encoding=_IMAGE_ENCODING,
            step=_IMAGE_STEP,
            data=bytes(data),
        )
