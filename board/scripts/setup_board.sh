#!/bin/sh
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

ROS_ROOT=/opt/ros/jazzy
WS="$REPO_ROOT/ros2_ws"

echo "============================================================"
echo " BeagleV-Fire SpaceWire setup"
echo "============================================================"

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: Run this script as root on the BeagleV-Fire."
    exit 1
fi

if [ ! -f "$ROS_ROOT/local_setup.sh" ]; then
    echo "ERROR: ROS 2 Jazzy not found at $ROS_ROOT"
    exit 1
fi

if [ ! -d "$WS/src/spacewire_gateway" ]; then
    echo "ERROR: SpaceWire gateway package not found:"
    echo "  $WS/src/spacewire_gateway"
    exit 1
fi

if ! command -v colcon >/dev/null 2>&1; then
    echo "ERROR: colcon not found."
    exit 1
fi

chmod +x "$REPO_ROOT/scripts/"*.sh

export COLCON_CURRENT_PREFIX="$ROS_ROOT"
. "$ROS_ROOT/local_setup.sh" 2>/dev/null || true

export PATH="$ROS_ROOT/bin:$PATH"
export AMENT_PREFIX_PATH="$ROS_ROOT"
export PYTHONPATH="$ROS_ROOT/lib/python3.12/site-packages"

cd "$WS"

echo
echo "Building SpaceWire ROS 2 workspace..."

rm -rf build install log
colcon build

echo
echo "============================================================"
echo " Setup complete"
echo "============================================================"
echo
echo "Normal startup:"
echo "  $REPO_ROOT/scripts/run_gateway.sh"
echo
echo "Program main FPGA:"
echo "  $REPO_ROOT/scripts/program_main_board.sh"
