#!/usr/bin/env python3
"""
spw_debug.py

BeagleV-Fire SpaceWire + DMA debugger.

Python remains the main debugger/UI.
Low-level physical register transactions are delegated to devmem2 through
DevMem2Access, because that path is proven to work correctly on this board.

Required files in the same directory:
    acces_layer.py
    spacewire.py
    devmem2_access.py
    spw_debug.py

Run as root.

Examples:
    python3 spw_debug.py status
    python3 spw_debug.py set-divider 0x18
    python3 spw_debug.py clear-errors
    python3 spw_debug.py start-link

    python3 spw_debug.py dma-prepare 5
    python3 spw_debug.py send 51 52 53 54 55
    python3 spw_debug.py dma-read 5
"""

import argparse
import mmap
import os
import struct
import time

from .devmem2_access import DevMem2Access
from .spacewire import spacewire_type


SPW_BASE = 0x45000000

DMA_STATUS       = 0x60000010
DMA_MASK         = 0x60000014
DMA_CLEAR        = 0x60000018
DMA_STREAM0_DESC = 0x60000460

DESC_ADDR   = 0xC4000000
RX_BUF      = 0xC4001000
DESC_CONFIG = 0x0000000D

TX_EOP = 0x100
TX_EEP = 0x101


# ----------------------------------------------------------------------
# Fast bulk DDR access
# ----------------------------------------------------------------------
#
# Keep devmem2 for control/status registers because that path is already
# proven on the board.  For a large DMA buffer, however, launching devmem2
# once per 32-bit word is extremely slow.  /dev/mem + mmap lets us clear or
# read the complete contiguous DDR range in one mapping.
#
def _map_phys(fd, address, size, prot):
    page_size = mmap.PAGESIZE
    page_base = address & ~(page_size - 1)
    page_offset = address - page_base

    mm = mmap.mmap(
        fd,
        page_offset + size,
        flags=mmap.MAP_SHARED,
        prot=prot,
        offset=page_base,
    )
    return mm, page_offset


def phys_zero(address, size):
    """Zero a contiguous physical-memory range using one mmap."""
    if size <= 0:
        return

    fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
    try:
        mm, offset = _map_phys(
            fd,
            address,
            size,
            mmap.PROT_READ | mmap.PROT_WRITE,
        )
        try:
            # For a MAP_SHARED /dev/mem mapping the slice assignment writes
            # directly to the physical DDR mapping. mmap.flush() maps to
            # msync(), which this /dev/mem mapping rejects with EINVAL on the
            # BeagleV-Fire kernel, so no explicit flush is needed here.
            mm[offset:offset + size] = b"\x00" * size
        finally:
            mm.close()
    finally:
        os.close(fd)


def phys_write(address, data):
    """Write bytes to a contiguous physical-memory range using one mmap."""
    if not data:
        return

    fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
    try:
        mm, offset = _map_phys(
            fd,
            address,
            len(data),
            mmap.PROT_READ | mmap.PROT_WRITE,
        )
        try:
            mm[offset:offset + len(data)] = data
        finally:
            mm.close()
    finally:
        os.close(fd)


def phys_read(address, size):
    """Read a contiguous physical-memory range using one mmap."""
    if size <= 0:
        return b""

    fd = os.open("/dev/mem", os.O_RDONLY | os.O_SYNC)
    try:
        mm, offset = _map_phys(fd, address, size, mmap.PROT_READ)
        try:
            return bytes(mm[offset:offset + size])
        finally:
            mm.close()
    finally:
        os.close(fd)


class Debugger:
    def __init__(self, access=None):
        self.access = access if access is not None else DevMem2Access()

        # The generated IP-XACT Python model describes the SpaceWire APB block.
        self.spw = spacewire_type(
            parent=None,
            base_address=SPW_BASE,
            access_layer=self.access,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def reg_addr(self, reg):
        return self.spw.get_base_address() + reg.get_address_offset()

    def read_reg(self, reg):
        return self.access.read32(self.reg_addr(reg))

    def write_reg(self, reg, value):
        return self.access.write32(self.reg_addr(reg), value)

    def status_raw(self):
        return self.read_reg(self.spw.status)

    def errors_raw(self):
        return self.read_reg(self.spw.errors)

    # ------------------------------------------------------------------
    # SpaceWire
    # ------------------------------------------------------------------

    def print_status(self):
        status = self.status_raw()
        errors = self.errors_raw()

        print()
        print("SpaceWire")
        print("---------")
        print(f"ID             : 0x{self.read_reg(self.spw.id):08X}")
        print(f"CONTROL        : 0x{self.read_reg(self.spw.control):08X}")
        print(f"STATUS         : 0x{status:08X}")
        print(f"  started      : {'YES' if self.spw.status.started else 'no'}")
        print(f"  connecting   : {'YES' if self.spw.status.connecting else 'no'}")
        print(f"  running      : {'YES' if self.spw.status.running else 'no'}")
        print(f"  TX ready     : {'YES' if self.spw.status.tx_ready else 'no'}")
        print(f"  TX half full : {'YES' if self.spw.status.tx_half_full else 'no'}")
        print(f"  RX valid     : {'YES' if self.spw.status.rx_valid else 'no'}")
        print(f"  RX half full : {'YES' if self.spw.status.rx_half_full else 'no'}")
        print(f"TX divider     : 0x{self.read_reg(self.spw.tx_divider):08X}")
        print(f"ERRORS         : 0x{errors:08X}")
        print(f"  disconnect   : {'YES' if (errors & 0x1) else 'no'}")
        print(f"  parity       : {'YES' if (errors & 0x2) else 'no'}")
        print(f"  escape       : {'YES' if (errors & 0x4) else 'no'}")
        print(f"  credit       : {'YES' if (errors & 0x8) else 'no'}")

        print()
        print("DMA")
        print("---")
        print(f"STATUS         : 0x{self.access.read32(DMA_STATUS):08X}")
        print(f"DESC config    : 0x{self.access.read32(DESC_ADDR + 0x0):08X}")
        print(f"DESC count     : 0x{self.access.read32(DESC_ADDR + 0x4):08X}")
        print(f"DESC dest      : 0x{self.access.read32(DESC_ADDR + 0x8):08X}")

    def set_divider(self, value):
        # Whole-register write: one bus transaction.
        rb = self.write_reg(self.spw.tx_divider, value)
        print(f"TX divider readback=0x{rb:08X}")

    def clear_errors(self):
        # ERRORS is W1C in the APB wrapper, despite normal fields being read-only.
        self.write_reg(self.spw.errors, 0xF)
        print(f"ERRORS=0x{self.errors_raw():08X}")

    def start_link(self):
        # First clear LINK_DISABLE/AUTOSTART/etc, then request start.
        self.write_reg(self.spw.control, 0x0)
        self.write_reg(self.spw.control, 0x1)

        deadline = time.monotonic() + 3.0
        last = self.status_raw()

        while time.monotonic() < deadline:
            last = self.status_raw()
            if last & 0x4:
                break
            time.sleep(0.05)

        print(f"CONTROL=0x{self.read_reg(self.spw.control):08X}")
        print(f"STATUS =0x{last:08X}")

    def stop_link(self):
        rb = self.write_reg(self.spw.control, 0x4)
        print(f"CONTROL readback=0x{rb:08X}")
        print(f"STATUS=0x{self.status_raw():08X}")

    def led(self, value):
        rb = self.write_reg(self.spw.led, 1 if value else 0)
        print(f"LED readback=0x{rb:08X}")

    def wait_tx_ready(self, timeout=2.0):
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            status = self.status_raw()
            if status & 0x8:
                return status
            time.sleep(0.01)

        raise TimeoutError(
            f"TX_READY timeout; STATUS=0x{self.status_raw():08X}"
        )

    def send(self, data, eop=True):
        if not (self.status_raw() & 0x4):
            print(
                f"WARNING: link is not RUNNING "
                f"(STATUS=0x{self.status_raw():08X})"
            )

        print("Sending:", " ".join(f"{x:02X}" for x in data),
              "+ EOP" if eop else "")

        for index, byte in enumerate(data):
            before = self.wait_tx_ready()

            # TX_DATA has a hardware side effect on each write.
            # Therefore always perform exactly ONE whole-register write.
            self.write_reg(self.spw.tx_data, byte)

            after = self.status_raw()
            errors = self.errors_raw()

            print(
                f"  byte {index}: 0x{byte:02X}  "
                f"before=0x{before:08X} after=0x{after:08X} "
                f"errors=0x{errors:08X}"
            )

        if eop:
            before = self.wait_tx_ready()
            self.write_reg(self.spw.tx_data, TX_EOP)
            after = self.status_raw()

            print(
                f"  EOP       : 0x100 "
                f"before=0x{before:08X} after=0x{after:08X}"
            )

        print(f"Final ERRORS=0x{self.errors_raw():08X}")

    # ------------------------------------------------------------------
    # DMA
    # ------------------------------------------------------------------

    def dma_status_raw(self):
        """Return the raw CoreAXI4DMAController status register."""
        return self.access.read32(DMA_STATUS)

    def dma_complete(self):
        """Return True when the current DMA receive completed."""
        return bool(self.dma_status_raw() & 0x1)

    def dma_error_bits(self):
        """Return DMA error bits [3:1] (0 means no DMA error)."""
        return self.dma_status_raw() & 0xE

    def dma_read_bytes(self, count):
        """
        Return exactly `count` bytes from the DMA RX DDR buffer.

        This is intentionally non-printing and uses the same fast mmap path
        as dma-read.  It is the application/ROS-facing API.
        """
        if count <= 0:
            raise ValueError("DMA count must be > 0")
        return phys_read(RX_BUF, count)

    def spacewire_snapshot(self):
        """
        Return a non-printing snapshot suitable for diagnostics/application code.
        """
        return {
            "control": self.read_reg(self.spw.control),
            "status": self.status_raw(),
            "errors": self.errors_raw(),
            "tx_divider": self.read_reg(self.spw.tx_divider),
            "id": self.read_reg(self.spw.id),
        }

    def print_dma_status(self):
        status = self.dma_status_raw()
        stream_desc = self.access.read32(DMA_STREAM0_DESC)

        # CoreAXI4DMAController INTR_0_STAT_REG:
        #   [9:4] descriptor number
        #   bit3  invalid buffer descriptor
        #   bit2  AXI read error
        #   bit1  AXI write error
        #   bit0  operation complete
        print("DMA")
        print("---")
        print(f"STATUS         : 0x{status:08X}")
        print(f"  DESC_RNUM    : {(status >> 4) & 0x3F}")
        print(f"  invalid desc : {'YES' if status & 0x8 else 'no'}")
        print(f"  AXI read err : {'YES' if status & 0x4 else 'no'}")
        print(f"  AXI write err: {'YES' if status & 0x2 else 'no'}")
        print(f"  complete     : {'YES' if status & 0x1 else 'no'}")
        print(f"STREAM0_DESC   : 0x{stream_desc:08X}")
        print(f"DESC config    : 0x{self.access.read32(DESC_ADDR + 0x0):08X}")
        print(f"DESC count     : 0x{self.access.read32(DESC_ADDR + 0x4):08X}")
        print(f"DESC dest      : 0x{self.access.read32(DESC_ADDR + 0x8):08X}")

    def clear_dma_events(self, max_attempts=16):
        history = []

        for _ in range(max_attempts):
            status = self.access.read32(DMA_STATUS)
            history.append(status)

            # Only [3:0] are clearable event/error bits.  [9:4] is the
            # descriptor-number field and is expected to remain set.
            if (status & 0xF) == 0:
                break

            self.access.write32(DMA_CLEAR, 0xF)

        return history

    def dma_prepare(self, count):
        if count <= 0:
            raise ValueError("DMA count must be > 0")

        history = self.clear_dma_events()

        # Keep the existing useful behaviour of clearing the destination plus
        # one sentinel word, but do it in ONE mmap instead of thousands of
        # separate devmem2 processes.
        phys_zero(RX_BUF, count + 4)

        # Descriptor lives in normal DDR, not side-effect MMIO.
        # Write config/count/destination together using one mmap operation.
        phys_write(
            DESC_ADDR,
            struct.pack(
                "<III",
                DESC_CONFIG,
                count,
                RX_BUF,
            ),
        )

        self.access.write32(DMA_MASK, 0x1)
        self.access.write32(DMA_STREAM0_DESC, DESC_ADDR)

        print("DMA receiver prepared")
        print("  cleared status :", " -> ".join(
            f"0x{x:08X}" for x in history
        ))
        print("  RX clear       : fast mmap")
        print(f"  config         : 0x{self.access.read32(DESC_ADDR + 0x0):08X}")
        print(f"  count          : {self.access.read32(DESC_ADDR + 0x4)}")
        print(f"  destination    : 0x{self.access.read32(DESC_ADDR + 0x8):08X}")
        print(f"  STREAM0_DESC   : 0x{self.access.read32(DMA_STREAM0_DESC):08X}")
        print(f"  DMA status     : 0x{self.access.read32(DMA_STATUS):08X}")

    def dma_read(self, count, wait=False, timeout=5.0):
        if count <= 0:
            raise ValueError("DMA count must be > 0")

        if wait:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                status = self.access.read32(DMA_STATUS)

                # Operation complete.
                if status & 0x1:
                    break

                # Abort the wait on a real DMA error.
                if status & 0xE:
                    break

                time.sleep(0.05)

        dma_status = self.access.read32(DMA_STATUS)
        desc_cfg = self.access.read32(DESC_ADDR + 0x0)

        # Read the complete receive region with one mmap instead of one
        # devmem2 process per 32-bit word.
        packet = phys_read(RX_BUF, count)

        print(f"DMA status : 0x{dma_status:08X}")
        print(f"Descriptor : 0x{desc_cfg:08X}")

        # Preserve the convenient full dump for small tests.  For image-sized
        # transfers, avoid filling the terminal with thousands of bytes.
        if count <= 256:
            nwords = (count + 3) // 4
            padded = packet + b"\x00" * (nwords * 4 - len(packet))

            for i in range(nwords):
                word = struct.unpack_from("<I", padded, 4 * i)[0]
                print(f"DDR 0x{RX_BUF + 4*i:08X}: 0x{word:08X}")

            print("Bytes      :", " ".join(f"{x:02X}" for x in packet))
        else:
            print("First 32   :", " ".join(f"{x:02X}" for x in packet[:32]))
            print("Last 16    :", " ".join(f"{x:02X}" for x in packet[-16:]))
            print(f"Bytes read : {len(packet)}")

        print(f"SPW status : 0x{self.status_raw():08X}")
        print(f"SPW errors : 0x{self.errors_raw():08X}")

    def dma_reset(self):
        """
        Pulse the FPGA-local DMA + RX-bridge reset.

        The reset is intentionally refused while SpaceWire is RUNNING because
        our hardware test showed that releasing the RX bridge while traffic is
        still present can feed the freshly-reset DMA before STREAM0_DESC has
        been restored.  Use dma-recover <count> for the complete safe sequence.
        """
        if self.status_raw() & 0x4:
            raise RuntimeError(
                "SpaceWire is RUNNING. Use 'dma-recover <count>' "
                "or run stop-link before dma-reset."
            )

        before = self.access.read32(DMA_STATUS)
        ptr_before = self.access.read32(DMA_STREAM0_DESC)

        # DEBUG_CONTROL bit 1 is a pulse requesting local DMA/RX recovery.
        self.access.write32(SPW_BASE + 0x38, 0x2)
        time.sleep(0.05)

        history = self.clear_dma_events()

        after = self.access.read32(DMA_STATUS)
        ptr_after = self.access.read32(DMA_STREAM0_DESC)

        print("DMA/RX bridge reset pulsed")
        print(f"  status before : 0x{before:08X}")
        print(f"  pointer before: 0x{ptr_before:08X}")
        print("  clear history :", " -> ".join(
            f"0x{x:08X}" for x in history
        ))
        print(f"  status after  : 0x{after:08X}")
        print(f"  pointer after : 0x{ptr_after:08X}")
        print("  run dma-prepare before receiving data")

    def dma_recover(self, count):
        """
        Proven recovery sequence after an interrupted/bad DMA receive:

          1. stop SpaceWire
          2. wait for link/RX traffic to settle
          3. clear SpaceWire sticky errors
          4. pulse local DMA + RX-bridge reset
          5. clear DMA event/error bits
          6. create and arm a fresh DMA descriptor
          7. clear any reset-related SpaceWire sticky error
          8. restart SpaceWire

        Linux, DDR and the rest of the FPGA stay running.
        """
        if count <= 0:
            raise ValueError("DMA count must be > 0")

        print("DMA recovery")
        print("------------")

        print("[1] Stop SpaceWire link")
        self.stop_link()
        time.sleep(0.20)

        print("[2] Clear SpaceWire errors")
        self.clear_errors()

        print("[3] Reset DMA + RX bridge")
        self.dma_reset()

        print("[4] Prepare fresh DMA descriptor")
        self.dma_prepare(count)

        # The local bridge reset can itself leave a sticky disconnect indication.
        # Clear it while the link is still stopped so the post-recovery status is
        # meaningful.
        print("[5] Clear SpaceWire errors after reset")
        self.clear_errors()

        print("[6] Restart SpaceWire link")
        self.start_link()

        status = self.status_raw()
        print()
        print("Recovery result")
        print(f"  SPW status     : 0x{status:08X}")
        print(f"  SPW errors     : 0x{self.errors_raw():08X}")
        print(f"  DMA status     : 0x{self.access.read32(DMA_STATUS):08X}")
        print(f"  STREAM0_DESC   : 0x{self.access.read32(DMA_STREAM0_DESC):08X}")

        if status & 0x4:
            print("  link           : RUNNING")
        else:
            print("  link           : NOT RUNNING")


def hex_byte(text):
    value = int(text, 16)
    if not 0 <= value <= 0xFF:
        raise argparse.ArgumentTypeError(
            f"{text!r} is not an 8-bit hexadecimal byte"
        )
    return value


def main():
    parser = argparse.ArgumentParser(
        description="BeagleV-Fire SpaceWire/DMA debugger"
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status")
    sub.add_parser("clear-errors")
    sub.add_parser("start-link")
    sub.add_parser("stop-link")
    sub.add_parser("dma-status")
    sub.add_parser("dma-reset")

    p = sub.add_parser("set-divider")
    p.add_argument("value", type=lambda x: int(x, 0))

    p = sub.add_parser("led")
    p.add_argument("value", choices=("0", "1"))

    p = sub.add_parser("send")
    p.add_argument("bytes", nargs="+", type=hex_byte)
    p.add_argument("--no-eop", action="store_true")

    p = sub.add_parser("dma-prepare")
    p.add_argument("count", type=lambda x: int(x, 0))

    p = sub.add_parser("dma-read")
    p.add_argument("count", type=lambda x: int(x, 0))
    p.add_argument("--wait", action="store_true")
    p.add_argument("--timeout", type=float, default=5.0)

    p = sub.add_parser("dma-recover")
    p.add_argument("count", type=lambda x: int(x, 0))

    p = sub.add_parser("read")
    p.add_argument("address", type=lambda x: int(x, 0))

    p = sub.add_parser("write")
    p.add_argument("address", type=lambda x: int(x, 0))
    p.add_argument("value", type=lambda x: int(x, 0))

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    dbg = Debugger()

    if args.command == "status":
        dbg.print_status()

    elif args.command == "clear-errors":
        dbg.clear_errors()

    elif args.command == "start-link":
        dbg.start_link()

    elif args.command == "stop-link":
        dbg.stop_link()

    elif args.command == "dma-status":
        dbg.print_dma_status()

    elif args.command == "dma-reset":
        dbg.dma_reset()

    elif args.command == "set-divider":
        dbg.set_divider(args.value)

    elif args.command == "led":
        dbg.led(args.value == "1")

    elif args.command == "send":
        dbg.send(args.bytes, eop=not args.no_eop)

    elif args.command == "dma-prepare":
        dbg.dma_prepare(args.count)

    elif args.command == "dma-read":
        dbg.dma_read(
            args.count,
            wait=args.wait,
            timeout=args.timeout,
        )

    elif args.command == "dma-recover":
        dbg.dma_recover(args.count)

    elif args.command == "read":
        print(
            f"0x{args.address:08X} = "
            f"0x{dbg.access.read32(args.address):08X}"
        )

    elif args.command == "write":
        rb = dbg.access.write32(args.address, args.value)
        print(
            f"0x{args.address:08X} <- "
            f"0x{args.value & 0xFFFFFFFF:08X}; "
            f"readback=0x{rb:08X}"
        )


if __name__ == "__main__":
    main()
