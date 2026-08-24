#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PC_ROOT="$SCRIPT_DIR"
WS="$PC_ROOT/ros2_ws"
GUI="$PC_ROOT/gui"

source /opt/ros/jazzy/setup.bash

if [ ! -f "$WS/install/setup.bash" ]; then
    echo "ERROR: PC ROS workspace has not been built."
    echo "Run:"
    echo "  $PC_ROOT/setup_pc.sh"
    exit 1
fi

source "$WS/install/setup.bash"

exec ros2 launch spacewire_pc spacewire_pc.launch.py \
    gui_dir:="$GUI"
