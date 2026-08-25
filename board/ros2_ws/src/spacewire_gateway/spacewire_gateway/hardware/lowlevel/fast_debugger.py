"""Optimized BeagleV-Fire SpaceWire low-level backend."""

import ctypes
import mmap
import os
import struct
from pathlib import Path

from .hybrid_access import HybridAccess
from .spw_debug_devmem2 import (
    Debugger,
    DMA_STATUS,
    DMA_CLEAR,
    DMA_MASK,
    DMA_STREAM0_DESC,
    DESC_ADDR,
    DESC_CONFIG,
    RX_BUF,
    TX_EOP,
)


_NATIVE_LIBRARY = Path(__file__).with_name("libmmio32.so")

_SPW_STATUS = 0x45000004
_SPW_TX_DATA = 0x45000008

_DDR_SIZE = 0x5000
_RX_OFFSET = RX_BUF - DESC_ADDR


class NativeAccess(HybridAccess):
    """Fast reads plus native 32-bit MMIO writes."""

    _FAST_WRITE_REGS = {
        DMA_CLEAR,
        DMA_MASK,
        DMA_STREAM0_DESC,
    }

    def __init__(self):
        super().__init__()

        self._lib = ctypes.CDLL(str(_NATIVE_LIBRARY))

        self._lib.mmio32_write.argtypes = [
            ctypes.c_uint64,
            ctypes.c_uint32,
        ]
        self._lib.mmio32_write.restype = ctypes.c_int

        self._lib.mmio32_tx_sequence.argtypes = [
            ctypes.c_uint64,
            ctypes.c_uint64,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_size_t,
            ctypes.c_uint64,
        ]
        self._lib.mmio32_tx_sequence.restype = ctypes.c_int

        self._lib.mmio32_close.argtypes = []
        self._lib.mmio32_close.restype = None

    def write32(self, address, value):
        value &= 0xFFFFFFFF

        if address in self._FAST_WRITE_REGS:
            rc = self._lib.mmio32_write(
                address,
                value,
            )

            if rc != 0:
                raise RuntimeError(
                    f"Native MMIO write failed at "
                    f"0x{address:08X}: rc={rc}"
                )

            return value

        return super().write32(address, value)

    def tx_sequence(self, words, timeout_s=2.0):
        values = list(words)

        if not values:
            return

        array = (ctypes.c_uint32 * len(values))(
            *values
        )

        rc = self._lib.mmio32_tx_sequence(
            _SPW_STATUS,
            _SPW_TX_DATA,
            array,
            len(values),
            int(timeout_s * 1_000_000_000),
        )

        if rc != 0:
            raise RuntimeError(
                f"Native SpaceWire TX failed: rc={rc}"
            )

    def close(self):
        try:
            if self._lib is not None:
                self._lib.mmio32_close()
                self._lib = None
        finally:
            super().close()
class FastDebugger(Debugger):
    """Debugger-compatible optimized application backend."""

    def __init__(self):
        self._fast_access = NativeAccess()
        super().__init__(access=self._fast_access)

        self._ddr_fd = os.open(
            "/dev/mem",
            os.O_RDWR | os.O_SYNC,
        )

        self._ddr = mmap.mmap(
            self._ddr_fd,
            _DDR_SIZE,
            flags=mmap.MAP_SHARED,
            prot=mmap.PROT_READ | mmap.PROT_WRITE,
            offset=DESC_ADDR,
        )

    def dma_prepare(self, count):
        if count <= 0:
            raise ValueError("DMA count must be > 0")

        for _ in range(16):
            status = self.access.read32(DMA_STATUS)

            if (status & 0xF) == 0:
                break

            self.access.write32(
                DMA_CLEAR,
                0xF,
            )
        else:
            raise RuntimeError(
                "DMA event bits did not clear"
            )

        self._ddr[
            _RX_OFFSET:_RX_OFFSET + count + 4
        ] = b"\x00" * (count + 4)

        struct.pack_into(
            "<III",
            self._ddr,
            0,
            DESC_CONFIG,
            count,
            RX_BUF,
        )

        self.access.write32(
            DMA_MASK,
            0x1,
        )

        self.access.write32(
            DMA_STREAM0_DESC,
            DESC_ADDR,
        )

    def dma_read_bytes(self, count):
        if count <= 0:
            raise ValueError("DMA count must be > 0")

        return bytes(
            self._ddr[
                _RX_OFFSET:_RX_OFFSET + count
            ]
        )

    def send(self, data, eop=True):
        if not (self.status_raw() & 0x4):
            raise RuntimeError(
                f"SpaceWire link is not RUNNING "
                f"(STATUS=0x{self.status_raw():08X})"
            )

        words = [
            int(value) & 0xFFFFFFFF
            for value in data
        ]

        if eop:
            words.append(TX_EOP)

        self._fast_access.tx_sequence(words)

        errors = self.errors_raw()

        if errors != 0:
            raise RuntimeError(
                f"SpaceWire ERRORS=0x{errors:08X}"
            )

    def close(self):
        try:
            if self._ddr is not None:
                self._ddr.close()
                self._ddr = None

            if self._ddr_fd is not None:
                os.close(self._ddr_fd)
                self._ddr_fd = None
        finally:
            self._fast_access.close()
