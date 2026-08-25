#!/bin/sh
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BOARD_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

LOWLEVEL="$BOARD_ROOT/ros2_ws/src/spacewire_gateway/spacewire_gateway/hardware/lowlevel"
SOURCE="$LOWLEVEL/mmio32.c"
OUTPUT="$LOWLEVEL/libmmio32.so"

COMPILER=riscv64-linux-gnu-gcc

echo "============================================================"
echo " Build BeagleV-Fire MMIO helper"
echo "============================================================"

if ! command -v "$COMPILER" >/dev/null 2>&1; then
    echo "ERROR: $COMPILER not found."
    echo
    echo "On Ubuntu install it with:"
    echo "  sudo apt install gcc-riscv64-linux-gnu"
    exit 1
fi

if [ ! -f "$SOURCE" ]; then
    echo "ERROR: MMIO source not found:"
    echo "  $SOURCE"
    exit 1
fi

echo
echo "Source:"
echo "  $SOURCE"
echo
echo "Output:"
echo "  $OUTPUT"
echo

"$COMPILER" \
    -O2 \
    -fPIC \
    -shared \
    -Wall \
    -Wextra \
    -o "$OUTPUT" \
    "$SOURCE"

echo
echo "Built successfully:"
ls -lh "$OUTPUT"

if command -v file >/dev/null 2>&1; then
    echo
    file "$OUTPUT"
fi

echo
echo "============================================================"
echo " MMIO helper build complete"
echo "============================================================"
