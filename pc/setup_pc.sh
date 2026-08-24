#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$SCRIPT_DIR/ros2_ws"

if [ ! -f /opt/ros/jazzy/setup.bash ]; then
    echo "ERROR: ROS 2 Jazzy is not installed."
    exit 1
fi

source /opt/ros/jazzy/setup.bash

cd "$WS"

rm -rf build install log
colcon build --symlink-install

echo
echo "PC setup complete."
echo
echo "Start the application with:"
echo "  $SCRIPT_DIR/start_pc.sh"
