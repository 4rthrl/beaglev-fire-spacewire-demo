# Troubleshooting

This document lists the most common problems that may occur when setting up or running the BeagleV-Fire SpaceWire demonstrator.

# 1. ROS 2 Gateway Is Not Visible

On the PC:

```bash
source /opt/ros/jazzy/setup.bash
ros2 node list
```

The main gateway should appear as:

```text
/spacewire_gateway
```

If it does not appear:

1. verify that `run_gateway.sh` is still running on the main BeagleV-Fire;
2. verify that the PC and BeagleV-Fire are connected to the same Ethernet network;
3. confirm that the board can be reached:

```bash
ping 192.168.1.220
```

4. verify that both systems are using compatible ROS 2/DDS networking.

---

# 2. Gateway Does Not Start

On the main BeagleV-Fire, start the gateway with:

```sh
cd /root/beaglev-spacewire
./scripts/run_gateway.sh
```

If the ROS package cannot be found, rebuild the board workspace:

```sh
./scripts/setup_board.sh
```

A rebuild is required after changing or redeploying the board ROS package, but not after a normal reboot.

---

# 3. GUI Does Not Start

Start the PC application from the repository root:

```bash
./pc/start_pc.sh
```

If the Qt GUI reports an error related to the `xcb` platform plugin or `xcb-cursor`, install:

```bash
sudo apt update
sudo apt install libxcb-cursor0
```

Then start the application again.

---

# 4. PC ROS Workspace Has Not Been Built

If `start_pc.sh` reports that the PC workspace is missing, run:

```bash
./pc/setup_pc.sh
```

This builds:

```text
pc/ros2_ws/
```

The build only needs to be repeated after changes to the PC-side ROS package or on a new PC.

---

# 5. SpaceWire Link Does Not Reach RUNNING

Inspect the diagnostics:

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic echo /spacewire/diagnostics --once
```

A healthy connected state typically reports:

```text
CONTROL = 0x00000001
STATUS  = 0x0000000C
ERRORS  = 0x00000000
```

`0x0C` indicates:

```text
RUNNING
TX_READY
```

A healthy disconnected state normally reports:

```text
STATUS = 0x00000008
```

If the link does not reach RUNNING:

- verify the physical SpaceWire connection;
- verify that both FPGA designs are programmed correctly;
- inspect the SpaceWire error flags;
- verify that the mock-camera board is powered.

---

# 6. SpaceWire Protocol Errors

The gateway monitors:

- disconnect errors;
- parity errors;
- escape errors;
- credit errors.

A healthy system should normally report:

```text
ERRORS = 0x00000000
```

If errors occur repeatedly, inspect the physical link and FPGA configuration before debugging the ROS layer.

---

# 7. Camera Request Is Accepted but No Image Arrives

The image request service only starts the transfer.

The image itself is published asynchronously on:

```text
/spacewire/camera/image
```

Check whether an image is being published:

```bash
ros2 topic echo /spacewire/camera/image --once
```

Also inspect the gateway terminal on the main BeagleV-Fire.

During a normal request it should show that:

1. the DMA receiver was prepared;
2. the camera command was transmitted;
3. the SpaceWire error register remained clear.

If the transfer times out, the hardware backend contains bounded DMA recovery and retry logic.

Persistent failures may indicate:

- incorrect FPGA gateware;
- a SpaceWire link problem;
- a DMA receive problem;
- the mock-camera FPGA not responding.

---

# 8. Wrong or Unexpected Image Pattern

Check the current gateway parameter:

```bash
ros2 param get /spacewire_gateway pattern
```

Set a pattern manually:

```bash
ros2 param set /spacewire_gateway pattern 4
```

Valid values are:

```text
0  Color boxes / grid
1  Solid red
2  Solid green
3  Solid blue
4  Vertical color bars
5  Horizontal color bars
6  Horizontal black-to-white gradient
7  Vertical black-to-white gradient
```

Then request a new image.

---

# 9. FPGA Needs to Be Programmed Again

The included programming scripts are:

```text
board/scripts/program_main_board.sh
board/scripts/program_mock_camera.sh
```

Main board:

```sh
./scripts/program_main_board.sh
```

Mock-camera board:

```sh
./scripts/program_mock_camera.sh
```

Programming is normally only necessary after intentionally changing the FPGA design or restoring a different board configuration.

A standard power cycle does not normally require FPGA reprogramming.

---

# 10. Duplicate or Stale ROS Processes

Unexpected duplicate messages or behaviour can occur if an older gateway or GUI process is still running.

Check:

```bash
ros2 node list
```

During normal operation there should be one instance of:

```text
/spacewire_gateway
/spacewire_gui
/spacewire_diagnostic_aggregator
```

Stop stale launch or gateway processes before starting a new instance.

---

# 11. Diagnostics Aggregator Is Missing

The SpaceWire link itself does not depend on the diagnostic aggregator.

If the raw diagnostics are available on:

```text
/spacewire/diagnostics
```

but the aggregated topics are missing, verify that the PC launch environment is running.

The aggregated topics are:

```text
/spacewire/diagnostics_agg
/spacewire/diagnostics_toplevel_state
```

Also verify that the ROS package is installed:

```bash
sudo apt install ros-jazzy-diagnostic-aggregator
```

---

# 12. Standalone Hardware Debugging

If the ROS layer needs to be bypassed, standalone low-level tools are available under:

```text
board/debug/spw_py/
```

These tools can be used to inspect:

- FPGA registers;
- SpaceWire status;
- error registers;
- DMA operation;
- received packets.

They are useful for determining whether a failure is located in:

```text
ROS 2
hardware backend
FPGA interface
SpaceWire link
DMA
```

For the hardware architecture, see [hardware.md](hardware.md).
