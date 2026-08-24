#!/usr/bin/env python3
import mmap
import os
import struct
import sys

DMA_STATUS = 0x60000010
RX_BUF = 0xC4001000

WIDTH = 64
HEIGHT = 64
HEADER_SIZE = 4
PIXEL_BYTES = WIDTH * HEIGHT * 3
TOTAL_BYTES = HEADER_SIZE + PIXEL_BYTES
EXPECTED_HEADER = bytes([0xC1, 0x02, WIDTH, HEIGHT])


def read_phys(addr, size):
    page_size = mmap.PAGESIZE
    page_base = addr & ~(page_size - 1)
    page_offset = addr - page_base
    map_size = page_offset + size

    fd = os.open("/dev/mem", os.O_RDONLY | os.O_SYNC)
    try:
        mm = mmap.mmap(
            fd,
            map_size,
            flags=mmap.MAP_SHARED,
            prot=mmap.PROT_READ,
            offset=page_base,
        )
        try:
            return mm[page_offset:page_offset + size]
        finally:
            mm.close()
    finally:
        os.close(fd)


def main():
    output_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "/root/spw_py/mock_camera.ppm"
    )

    dma_status = struct.unpack("<I", read_phys(DMA_STATUS, 4))[0]
    print(f"DMA status : 0x{dma_status:08X}")

    packet = read_phys(RX_BUF, TOTAL_BYTES)
    header = packet[:HEADER_SIZE]
    pixels = packet[HEADER_SIZE:]

    print("Header     :", " ".join(f"{b:02X}" for b in header))

    if header != EXPECTED_HEADER:
        raise SystemExit(
            "Bad header; expected C1 02 40 40. "
            "DMA may not have completed or the camera packet format is wrong."
        )

    if len(pixels) != PIXEL_BYTES:
        raise SystemExit(
            f"Expected {PIXEL_BYTES} RGB bytes, got {len(pixels)}"
        )

    # PPM P6 stores row-major RGB888 directly.
    with open(output_path, "wb") as f:
        f.write(f"P6\n{WIDTH} {HEIGHT}\n255\n".encode("ascii"))
        f.write(pixels)

    print(f"RGB bytes   : {len(pixels)}")
    print(f"Image saved : {output_path}")
    print("First 8 pixels:")
    for i in range(8):
        r, g, b = pixels[3*i:3*i+3]
        print(f"  pixel {i}: R={r:3d} G={g:3d} B={b:3d}")


if __name__ == "__main__":
    main()
