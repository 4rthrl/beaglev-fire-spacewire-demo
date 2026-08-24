#!/bin/sh
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

ROS_ROOT=/opt/ros/jazzy
WS="$REPO_ROOT/ros2_ws"
PKG_INSTALL="$WS/install/spacewire_gateway"

export COLCON_CURRENT_PREFIX="$ROS_ROOT"
. "$ROS_ROOT/local_setup.sh" 2>/dev/null || true

export PATH="$ROS_ROOT/bin:$PATH"
export AMENT_PREFIX_PATH="$PKG_INSTALL:$ROS_ROOT"
export PYTHONPATH="$PKG_INSTALL/lib/python3.12/site-packages:$ROS_ROOT/lib/python3.12/site-packages"

cd "$WS"

exec ros2 launch spacewire_gateway spacewire_gateway.launch.py
