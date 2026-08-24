# Installation and Setup

This document describes how to set up and run the BeagleV-Fire SpaceWire demonstrator from a fresh installation.

The demonstrator uses:

- one PC running Ubuntu 24.04 and ROS 2 Jazzy;
- one BeagleV-Fire as the main SpaceWire/ROS gateway;
- one BeagleV-Fire as an FPGA mock camera;
- a physical SpaceWire connection between both boards.

The network addresses used during development were:

| Device | Address |
|---|---|
| Main BeagleV-Fire | `192.168.1.220` |
| Mock-camera BeagleV-Fire | `192.168.1.223` |

Different addresses can be used if required.

---

# 1. Repository

Clone the repository on the PC:

```bash
git clone <repository-url>
cd beaglev-fire-spacewire-demo
```

The main directories are:

```text
board/      Software and gateware for the BeagleV-Fire boards
pc/         PC GUI and ROS 2 launch environment
hardware/   SpaceWire interface PCB
docs/       Detailed project documentation
```

---

# 2. PC Setup

## 2.1 Requirements

The PC requires:

- Ubuntu 24.04
- ROS 2 Jazzy
- Python 3
- colcon
- ROS 2 diagnostic aggregator
- PySide6
- `libxcb-cursor0`

ROS 2 Jazzy is expected at:

```text
/opt/ros/jazzy
```

Install the additional Ubuntu packages:

```bash
sudo apt update

sudo apt install \
    python3-colcon-common-extensions \
    ros-jazzy-diagnostic-aggregator \
    libxcb-cursor0
```

Install the GUI Python dependencies:

```bash
python3 -m pip install -r pc/gui/requirements.txt
python3 -m pip install -r pc/gui/requirements-ros.txt
```

## 2.2 Build the PC ROS workspace

From the repository root:

```bash
./pc/setup_pc.sh
```

This builds the ROS 2 workspace under:

```text
pc/ros2_ws/
```

This step only needs to be repeated on a new PC or after changing the PC-side ROS package.

---

# 3. Main BeagleV-Fire Setup

The main BeagleV-Fire runs the ROS 2 SpaceWire gateway and interfaces with the SpaceWire FPGA core.

The board image must provide:

- ROS 2 Jazzy under `/opt/ros/jazzy`;
- Python 3;
- colcon;
- `devmem2`;
- the Microchip gateware updater.

The gateware updater is expected at:

```text
/opt/microchip/gateware/update-gateware.sh
```

## 3.1 Copy the board files

From the PC:

```bash
scp -r board \
    root@192.168.1.220:/root/beaglev-spacewire
```

The main board will then contain:

```text
/root/beaglev-spacewire/
├── ros2_ws/
├── gateware/
├── debug/
└── scripts/
```

Connect to it:

```bash
ssh root@192.168.1.220
```

## 3.2 Build the board workspace

On the main BeagleV-Fire:

```sh
cd /root/beaglev-spacewire
./scripts/setup_board.sh
```

This builds the `spacewire_gateway` ROS 2 package.

The build does not need to be repeated after every reboot. It is only required after changing the gateway source or deploying the project to a new board image.

---

# 4. Main FPGA

The final main-board gateware is stored in:

```text
board/gateware/main_board/
├── dma_reset.spi
└── mpfs_dtbo.spi
```

To program the main FPGA:

```sh
cd /root/beaglev-spacewire
./scripts/program_main_board.sh
```

The script uses the Microchip gateware updater together with the included bitstream and device-tree overlay.

The programmed gateware persists across normal power cycles, so this step normally does not need to be repeated after every reboot.

---

# 5. Mock-Camera BeagleV-Fire

The second BeagleV-Fire emulates a camera entirely in FPGA logic.

It generates 64 × 64 RGB images and transmits them over SpaceWire to the main board.

No ROS application is required on this board during normal operation.

## 5.1 Copy the board files

From the PC:

```bash
scp -r board \
    root@192.168.1.223:/root/beaglev-spacewire
```

Connect to the board:

```bash
ssh root@192.168.1.223
```

## 5.2 Program the mock-camera FPGA

On the mock-camera BeagleV-Fire:

```sh
cd /root/beaglev-spacewire
./scripts/program_mock_camera.sh
```

The final mock-camera gateware is stored in:

```text
board/gateware/mock_camera/
├── mock_camera.spi
└── mpfs_dtbo.spi
```

After programming, no userspace application needs to run on the mock-camera board.

---

# 6. Hardware Connection

Before starting the application:

1. power both BeagleV-Fire boards;
2. connect the PC and main BeagleV-Fire to the same Ethernet network;
3. connect the two BeagleV-Fire boards through the SpaceWire interface;
4. verify that the PC can reach the main board.

For example:

```bash
ping 192.168.1.220
```

---

# 7. Normal Startup

Once the first-time installation has been completed, neither ROS workspace needs to be rebuilt during a normal startup.

## 7.1 Main BeagleV-Fire

From the PC:

```bash
ssh root@192.168.1.220
```

On the main BeagleV-Fire:

```sh
cd /root/beaglev-spacewire
./scripts/run_gateway.sh
```

The gateway should report messages similar to:

```text
SpaceWire Gateway started
Hardware backend: beaglev
```

Leave this process running.

## 7.2 PC

In another PC terminal, from the repository root:

```bash
./pc/start_pc.sh
```

This starts:

- the ROS 2 diagnostic aggregator;
- the PySide6 SpaceWire GUI.

The GUI can then be used to:

1. connect the SpaceWire link;
2. select an FPGA image pattern;
3. request an image;
4. display the received image;
5. inspect link status and errors;
6. disconnect the link.

---

# 8. ROS 2 Interface

The main ROS 2 topics are:

```text
/spacewire/diagnostics
/spacewire/diagnostics_agg
/spacewire/diagnostics_toplevel_state
/spacewire/camera/image
```

The main services are:

```text
/spacewire/link/connect
/spacewire/link/disconnect
/spacewire/camera/request_image
```

The main board runs:

```text
/spacewire_gateway
```

The PC normally runs:

```text
/spacewire_gui
/spacewire_diagnostic_aggregator
```

Image-pattern selection uses the `pattern` parameter of:

```text
/spacewire_gateway
```

For the complete interface, see [ros_interface.md](ros_interface.md).

---

# 9. Quick ROS Verification

Source ROS 2 on the PC:

```bash
source /opt/ros/jazzy/setup.bash
```

Check that the gateway is visible:

```bash
ros2 node list
```

Check the available services:

```bash
ros2 service list
```

Inspect the SpaceWire diagnostics:

```bash
ros2 topic echo /spacewire/diagnostics --once
```

A healthy but disconnected link should report that the link is disconnected without reporting SpaceWire protocol errors.

---

# 10. Updating the Software

## PC-side changes

After modifying:

```text
pc/ros2_ws/
```

rebuild with:

```bash
./pc/setup_pc.sh
```

Changes made only to the GUI source do not require a ROS workspace rebuild.

## Main-board changes

After modifying:

```text
board/ros2_ws/
```

deploy the updated board files and rebuild:

```sh
./scripts/setup_board.sh
```

Then restart the gateway:

```sh
./scripts/run_gateway.sh
```

---

# 11. Normal Power Cycle

After the complete system has already been installed:

## Mock-camera board

Power the board. No userspace program needs to be started.

## Main board

```sh
cd /root/beaglev-spacewire
./scripts/run_gateway.sh
```

## PC

```bash
./pc/start_pc.sh
```

No ROS rebuild or FPGA reprogramming is normally required after a standard power cycle.

---

# 12. Further Documentation

Additional information is available in:

- [Architecture](architecture.md)
- [ROS 2 interface](ros_interface.md)
- [Hardware](hardware.md)
- [Troubleshooting](troubleshooting.md)
