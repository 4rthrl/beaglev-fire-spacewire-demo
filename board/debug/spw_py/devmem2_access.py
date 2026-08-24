#!/usr/bin/env python3
import re
import shutil
import subprocess
from acces_layer import accesLayer

class DevMem2Access(accesLayer):
    def __init__(self, executable=None):
        self.executable = executable or shutil.which("devmem2")
        if not self.executable:
            raise RuntimeError("devmem2 was not found in PATH")

    def _run(self, *args):
        result = subprocess.run(
            [self.executable, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"devmem2 failed with exit code {result.returncode}:\n{result.stdout}"
            )
        return result.stdout

    @staticmethod
    def _extract_last_hex(output):
        values = re.findall(r"0x[0-9A-Fa-f]+", output)
        if not values:
            raise RuntimeError(
                "Could not find a hexadecimal value in devmem2 output:\n" + output
            )
        return int(values[-1], 16)

    def read32(self, addr):
        output = self._run(f"0x{addr:X}", "w")
        return self._extract_last_hex(output)

    def write32(self, addr, value):
        value &= 0xFFFFFFFF
        self._run(f"0x{addr:X}", "w", f"0x{value:X}")
        return self.read32(addr)

    def read_register(self, addr, offset=0, width=32):
        value = self.read32(addr)
        if offset == 0 and width == 32:
            return value
        mask = (1 << width) - 1
        return (value >> offset) & mask

    def write_register(self, addr, data):
        return self.write32(addr, data)

    def modify_register(self, addr, data, offset=0, width=32):
        old = self.read32(addr)
        if width == 32:
            mask = 0xFFFFFFFF
        else:
            mask = ((1 << width) - 1) << offset
        new = (old & ~mask) | ((data << offset) & mask)
        return self.write32(addr, new)
