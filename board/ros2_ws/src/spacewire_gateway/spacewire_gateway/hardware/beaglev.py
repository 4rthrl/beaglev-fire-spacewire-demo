"""BeagleV-Fire SpaceWire hardware backend.

This backend deliberately contains no ROS message imports.  It converts the
hardware packet into ReceivedImage; gateway.py remains responsible for creating
and publishing sensor_msgs/msg/Image.

Hardware image packet:
    C1 02 40 40 + 64*64*3 bytes RGB888

Flow:
    request_image()
        -> arm DMA for 12292 bytes
        -> send 12 PP 00 EOP to the FPGA mock camera

    poll_image()
        -> inspect DMA status without blocking
        -> on complete, mmap-read the DDR packet
        -> validate header
        -> return ReceivedImage(width=64, height=64, encoding='rgb8', ...)

"""

from __future__ import annotations

import time

from spacewire_gateway.hardware.base import (
    CameraHousekeeping,
    ReceivedImage,
    SpaceWireHardware,
    SpaceWireStatus,
)
from spacewire_gateway.hardware.lowlevel.fast_debugger import FastDebugger


_IMAGE_WIDTH = 64
_IMAGE_HEIGHT = 64
_IMAGE_ENCODING = "rgb8"
_IMAGE_STEP = _IMAGE_WIDTH * 3
_IMAGE_HEADER = bytes((0xC1, 0x02, 0x40, 0x40))
_IMAGE_DATA_BYTES = _IMAGE_WIDTH * _IMAGE_HEIGHT * 3
_IMAGE_PACKET_BYTES = len(_IMAGE_HEADER) + _IMAGE_DATA_BYTES

# Camera housekeeping response:
#   C1 F0 00 40
#   followed by the complete 256-byte register window (64 x 32-bit words).
_HOUSEKEEPING_HEADER = bytes((0xC1, 0xF0, 0x00, 0x40))
_HOUSEKEEPING_REGISTER_BYTES = 256
_HOUSEKEEPING_PACKET_BYTES = (
    len(_HOUSEKEEPING_HEADER) + _HOUSEKEEPING_REGISTER_BYTES
)

# FPGA command-handler pattern values are 0..7.
_MIN_PATTERN = 0
_MAX_PATTERN = 7

# A normal 64x64 RGB frame is far quicker than this.  This timeout only detects
# a receive that has genuinely stopped progressing.
_REQUEST_TIMEOUT_S = 1.5


class BeagleVSpaceWireHardware(SpaceWireHardware):

    def __init__(self, max_retries: int = 1) -> None:
        self._debugger = FastDebugger()

        self._current_pattern: int | None = None
        self._request_in_flight = False
        self._request_start_time: float | None = None
        self._retry_count = 0
        self._max_retries = max_retries

    # ------------------------------------------------------------------
    # Link control / diagnostics
    # ------------------------------------------------------------------

    def connect(self) -> tuple[bool, str]:
        snapshot = self._debugger.spacewire_snapshot()

        if snapshot["status"] & 0x4:
            return True, "SpaceWire link already running"

        self._debugger.clear_errors()
        self._debugger.start_link()

        snapshot = self._debugger.spacewire_snapshot()
        if snapshot["status"] & 0x4:
            return True, "SpaceWire link connected"

        return (
            False,
            f"SpaceWire link failed to reach RUNNING "
            f"(STATUS=0x{snapshot['status']:08X})",
        )

    def disconnect(self) -> tuple[bool, str]:
        snapshot = self._debugger.spacewire_snapshot()

        if not (snapshot["status"] & 0x4):
            self._clear_request_state()
            return True, "SpaceWire link already disconnected"

        self._debugger.stop_link()
        self._clear_request_state()

        snapshot = self._debugger.spacewire_snapshot()
        if snapshot["status"] & 0x4:
            return (
                False,
                f"SpaceWire link is still running "
                f"(STATUS=0x{snapshot['status']:08X})",
            )

        return True, "SpaceWire link disconnected"

    def get_status(self) -> SpaceWireStatus:
        snapshot = self._debugger.spacewire_snapshot()

        status = snapshot["status"]
        errors = snapshot["errors"]

        return SpaceWireStatus(
            started=bool(status & 0x1),
            connecting=bool(status & 0x2),
            running=bool(status & 0x4),
            tx_ready=bool(status & 0x8),
            tx_half_full=bool(status & 0x10),
            rx_valid=bool(status & 0x20),
            rx_half_full=bool(status & 0x40),
            disconnect_error=bool(errors & 0x1),
            parity_error=bool(errors & 0x2),
            escape_error=bool(errors & 0x4),
            credit_error=bool(errors & 0x8),
            tx_divider=snapshot["tx_divider"],
            control_raw=snapshot["control"],
            status_raw=status,
            errors_raw=errors,
            core_id=snapshot["id"],
        )

    # ------------------------------------------------------------------
    # Camera
    # ------------------------------------------------------------------

    def request_image(self, pattern: int) -> tuple[bool, str]:
        if self._request_in_flight:
            return False, "An image request is already in progress"

        snapshot = self._debugger.spacewire_snapshot()
        if not (snapshot["status"] & 0x4):
            return False, "SpaceWire link is not running"

        if not _MIN_PATTERN <= pattern <= _MAX_PATTERN:
            return False, f"Invalid pattern: {pattern}; expected 0..7"

        try:
            self._arm_and_send(pattern)
        except Exception as exc:
            self._clear_request_state()
            return False, f"Failed to start image request: {exc}"

        self._current_pattern = pattern
        self._request_in_flight = True
        self._request_start_time = time.monotonic()
        self._retry_count = 0

        return True, f"Camera image request accepted (pattern {pattern})"

    def poll_image(self) -> ReceivedImage | None:
        if not self._request_in_flight:
            return None

        dma_status = self._debugger.dma_status_raw()

        # DMA error: attempt the proven stop/reset/re-arm/restart recovery,
        # then resend the exact same camera request.
        if dma_status & 0xE:
            self._retry_or_abort(
                f"DMA error status 0x{dma_status:08X}"
            )
            return None

        if dma_status & 0x1:
            try:
                packet = self._debugger.dma_read_bytes(_IMAGE_PACKET_BYTES)
                image = self._packet_to_image(packet)
            except Exception as exc:
                self._retry_or_abort(f"Invalid received image: {exc}")
                return None

            self._clear_request_state()
            return image

        if (
            self._request_start_time is not None
            and time.monotonic() - self._request_start_time
            > _REQUEST_TIMEOUT_S
        ):
            self._retry_or_abort("DMA image receive timeout")

        return None

    def get_housekeeping(
        self,
    ) -> tuple[bool, str, CameraHousekeeping | None]:
        """Request and decode a complete camera housekeeping snapshot."""

        # Image reception and housekeeping share the same DMA receiver.
        if self._request_in_flight:
            return (
                False,
                "Cannot request housekeeping while an image request is active",
                None,
            )

        snapshot = self._debugger.spacewire_snapshot()
        if not (snapshot["status"] & 0x4):
            return False, "SpaceWire link is not running", None

        try:
            # Arm the same DMA receiver, now for the shorter HK packet.
            self._debugger.dma_prepare(_HOUSEKEEPING_PACKET_BYTES)

            # GET_HOUSEKEEPING = 0x30.
            # Debugger.send() appends SpaceWire EOP.
            self._debugger.send([0x30], eop=True)

            deadline = time.monotonic() + _REQUEST_TIMEOUT_S

            while True:
                dma_status = self._debugger.dma_status_raw()

                if dma_status & 0xE:
                    return (
                        False,
                        f"Housekeeping DMA error "
                        f"0x{dma_status:08X}",
                        None,
                    )

                if dma_status & 0x1:
                    break

                if time.monotonic() >= deadline:
                    return False, "Housekeeping receive timeout", None

                time.sleep(0.0002)

            packet = self._debugger.dma_read_bytes(
                _HOUSEKEEPING_PACKET_BYTES
            )
            registers = self._packet_to_housekeeping(packet)

        except Exception as exc:
            return False, f"Housekeeping request failed: {exc}", None

        return True, "Camera housekeeping received", registers

    def shutdown(self) -> None:
        self._clear_request_state()
        self._debugger.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _arm_and_send(self, pattern: int) -> None:
        self._debugger.dma_prepare(_IMAGE_PACKET_BYTES)

        # CONFIGURE_AND_START = 0x12
        # PP = FPGA pattern selector
        # BB = 0x00 (Bayer selection is irrelevant for direct RGB output)
        # Debugger.send() appends EOP.
        self._debugger.send([0x12, pattern, 0x00], eop=True)

    def _packet_to_housekeeping(
        self,
        packet: bytes,
    ) -> CameraHousekeeping:
        """Decode the FPGA register window into named housekeeping fields."""

        if len(packet) != _HOUSEKEEPING_PACKET_BYTES:
            raise ValueError(
                f"wrong housekeeping packet size {len(packet)}, "
                f"expected {_HOUSEKEEPING_PACKET_BYTES}"
            )

        header = packet[:4]
        if header != _HOUSEKEEPING_HEADER:
            raise ValueError(
                "bad housekeeping header: "
                + " ".join(f"{byte:02X}" for byte in header)
            )

        payload = packet[4:]

        registers = {
            offset: int.from_bytes(
                payload[offset:offset + 4],
                byteorder="big",
                signed=False,
            )
            for offset in range(0, _HOUSEKEEPING_REGISTER_BYTES, 4)
        }

        def signed32(value: int) -> int:
            if value & 0x80000000:
                return value - 0x100000000
            return value

        return CameraHousekeeping(
            device_id=registers[0x00],
            destination_address=registers[0x04],
            protocol_id=registers[0x08],
            protocol_version=registers[0x0C],
            fw_version=registers[0x10],
            register_map_version=registers[0x14],
            capabilities=registers[0x18],

            bist_status=registers[0x20],
            operating_mode=registers[0x24],
            image_source=registers[0x28],
            pattern=registers[0x2C],
            bayer=registers[0x30],
            camera_status=registers[0x34],
            last_error=registers[0x38],

            integration_time=registers[0x40],
            lup_config=registers[0x44],
            image_corrections=registers[0x48],
            nuc_lut_version=registers[0x4C],
            bp_lut_version=registers[0x50],
            test_pattern_a_version=registers[0x54],
            test_pattern_b_version=registers[0x58],
            image_size=registers[0x5C],

            tc_counter=registers[0x60],
            last_tc_id=registers[0x64],
            last_tc_status=registers[0x68],
            frame_counter=registers[0x6C],
            abort_counter=registers[0x70],
            command_error_counter=registers[0x74],
            uptime_seconds=registers[0x78],

            monitor_valid=registers[0x80],
            temp_detector=signed32(registers[0x84]),
            vdd20_voltage=registers[0x88],
            core_1v2_current=registers[0x8C],
            core_1v2_voltage=registers[0x90],
            io_3v3_current=registers[0x94],
            io_3v3_voltage=registers[0x98],
            input_5v_current=registers[0x9C],
            temp_fpga=signed32(registers[0xA0]),
            temp_power=signed32(registers[0xA4]),

            spw_rx_packet_counter=registers[0xC0],
            spw_tx_packet_counter=registers[0xC4],
            spw_error_counter=registers[0xC8],
            last_spw_error=registers[0xCC],
        )

    def _packet_to_image(self, packet: bytes) -> ReceivedImage:
        if len(packet) != _IMAGE_PACKET_BYTES:
            raise ValueError(
                f"wrong packet size {len(packet)}, "
                f"expected {_IMAGE_PACKET_BYTES}"
            )

        header = packet[:4]
        if header != _IMAGE_HEADER:
            raise ValueError(
                "bad camera header: "
                + " ".join(f"{byte:02X}" for byte in header)
            )

        rgb = packet[4:]

        if len(rgb) != _IMAGE_DATA_BYTES:
            raise ValueError(
                f"wrong RGB payload size {len(rgb)}, "
                f"expected {_IMAGE_DATA_BYTES}"
            )

        return ReceivedImage(
            width=_IMAGE_WIDTH,
            height=_IMAGE_HEIGHT,
            encoding=_IMAGE_ENCODING,
            step=_IMAGE_STEP,
            data=rgb,
        )

    def _retry_or_abort(self, reason: str) -> None:
        if self._current_pattern is None:
            self._clear_request_state()
            return

        if self._retry_count >= self._max_retries:
            print(
                f"[BeagleVSpaceWireHardware] {reason}; "
                f"maximum retries reached"
            )
            self._clear_request_state()
            return

        pattern = self._current_pattern
        self._retry_count += 1

        print(
            f"[BeagleVSpaceWireHardware] {reason}; "
            f"recovering and retrying image "
            f"({self._retry_count}/{self._max_retries})"
        )

        # dma_recover() is the hardware-tested sequence:
        # stop link -> clear errors -> local DMA/RX reset -> fresh descriptor
        # -> clear errors -> restart link.
        self._debugger.dma_recover(_IMAGE_PACKET_BYTES)

        # dma_recover has already armed the DMA descriptor, so only resend
        # the camera command here.
        self._debugger.send([0x12, pattern, 0x00], eop=True)
        self._request_start_time = time.monotonic()

    def _clear_request_state(self) -> None:
        self._current_pattern = None
        self._request_in_flight = False
        self._request_start_time = None
        self._retry_count = 0
