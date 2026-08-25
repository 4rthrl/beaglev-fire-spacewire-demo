#!/usr/bin/env python3

import mmap
import os
import struct

from .devmem2_access import DevMem2Access


class HybridAccess(DevMem2Access):
    """
    Fast reads through persistent read-only /dev/mem mappings.

    Writes deliberately remain on the proven devmem2 path inherited
    from DevMem2Access, so MMIO writes are still explicit 32-bit
    transactions with devmem2 readback verification.
    """

    def __init__(self, executable=None):
        super().__init__(executable=executable)

        self._page_size = mmap.PAGESIZE
        self._fd = os.open(
            "/dev/mem",
            os.O_RDONLY | os.O_SYNC,
        )
        self._mappings = {}

    def _get_mapping(self, addr):
        page_base = addr & ~(self._page_size - 1)

        mm = self._mappings.get(page_base)

        if mm is None:
            mm = mmap.mmap(
                self._fd,
                self._page_size,
                flags=mmap.MAP_SHARED,
                prot=mmap.PROT_READ,
                offset=page_base,
            )
            self._mappings[page_base] = mm

        return mm, addr - page_base

    def read32(self, addr):
        if addr & 0x3:
            raise ValueError(
                f"32-bit MMIO read requires aligned address: 0x{addr:X}"
            )

        mm, offset = self._get_mapping(addr)

        return struct.unpack_from(
            "<I",
            mm,
            offset,
        )[0]

    def close(self):
        for mm in self._mappings.values():
            try:
                mm.close()
            except Exception:
                pass

        self._mappings.clear()

        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
