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
    ReceivedImage,
    SpaceWireHardware,
    SpaceWireStatus,
)
from spacewire_gateway.hardware.lowlevel.spw_debug_devmem2 import Debugger


_IMAGE_WIDTH = 64
_IMAGE_HEIGHT = 64
_IMAGE_ENCODING = "rgb8"
_IMAGE_STEP = _IMAGE_WIDTH * 3
_IMAGE_HEADER = bytes((0xC1, 0x02, 0x40, 0x40))
_IMAGE_DATA_BYTES = _IMAGE_WIDTH * _IMAGE_HEIGHT * 3
_IMAGE_PACKET_BYTES = len(_IMAGE_HEADER) + _IMAGE_DATA_BYTES

# FPGA command-handler pattern values are 0..7.
_MIN_PATTERN = 0
_MAX_PATTERN = 7

# A normal 64x64 RGB frame is far quicker than this.  This timeout only detects
# a receive that has genuinely stopped progressing.
_REQUEST_TIMEOUT_S = 1.5


class BeagleVSpaceWireHardware(SpaceWireHardware):

    def __init__(self, max_retries: int = 1) -> None:
        self._debugger = Debugger()

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

    def shutdown(self) -> None:
        self._clear_request_state()

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
