#!/bin/sh
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

BITSTREAM="$REPO_ROOT/gateware/mock_camera/mock_camera.spi"
DEVICE_TREE="$REPO_ROOT/gateware/mock_camera/mpfs_dtbo.spi"

echo "Programming mock-camera BeagleV-Fire"
echo "  Bitstream   : $BITSTREAM"
echo "  Device tree : $DEVICE_TREE"

if [ ! -f "$BITSTREAM" ]; then
    echo "ERROR: Bitstream not found: $BITSTREAM"
    exit 1
fi

if [ ! -f "$DEVICE_TREE" ]; then
    echo "ERROR: Device tree not found: $DEVICE_TREE"
    exit 1
fi

/opt/microchip/gateware/update-gateware.sh \
    "$BITSTREAM" \
    "$DEVICE_TREE"
