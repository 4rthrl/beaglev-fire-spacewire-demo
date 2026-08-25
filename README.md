# BeagleV-Fire SpaceWire Demo

This repository contains a complete SpaceWire demonstration running on two BeagleV-Fire boards.

The main BeagleV-Fire runs a ROS 2 Jazzy SpaceWire gateway. A second BeagleV-Fire emulates a camera and sends generated 64 × 64 RGB images over a physical SpaceWire link.

A PySide6 GUI on the PC communicates with the gateway over ROS 2/DDS and allows the user to:

- connect and disconnect the SpaceWire link;
- select an FPGA-generated image pattern;
- request and display an image;
- request camera housekeeping and inspect the decoded register snapshot;
- monitor SpaceWire diagnostics.

## Architecture

```text
PC
├── PySide6 GUI
├── ROS 2 Jazzy
└── diagnostic_aggregator
        │
        │ DDS / Ethernet
        ▼
Main BeagleV-Fire
├── ROS 2 SpaceWire gateway
├── SpaceWire FPGA core
└── DMA image receiver
        │
        │ SpaceWire
        ▼
Mock-camera BeagleV-Fire
└── FPGA camera emulator
```

## Repository structure

```text
board/
├── ros2_ws/        ROS 2 SpaceWire gateway
├── gateware/       Main-board and mock-camera FPGA bitstreams
├── debug/          Standalone SpaceWire debug tools
└── scripts/        Board setup, startup and programming scripts

pc/
├── gui/            PySide6 SpaceWire control GUI
├── ros2_ws/        PC-side ROS launch and diagnostics
├── setup_pc.sh
└── start_pc.sh

hardware/
└── connector_board/
    KiCad source, fabrication files and custom components

docs/
└── Detailed project documentation
```

## First-time setup

### PC

ROS 2 Jazzy is required.

```bash
./pc/setup_pc.sh
```

See [docs/installation.md](docs/installation.md) for the complete installation procedure.

### Main BeagleV-Fire

Copy the `board/` directory to the BeagleV-Fire and run:

```sh
./scripts/setup_board.sh
```

The main FPGA can be programmed with:

```sh
./scripts/program_main_board.sh
```

The mock-camera FPGA can be programmed on the second board with:

```sh
./scripts/program_mock_camera.sh
```

## Normal startup

On the main BeagleV-Fire:

```sh
./scripts/run_gateway.sh
```

On the PC:

```bash
./pc/start_pc.sh
```

The GUI can then be used to connect the SpaceWire link, request camera images and refresh camera housekeeping.

## Documentation

Detailed documentation is available in [`docs/`](docs/):

- [Installation](docs/installation.md)
- [Architecture](docs/architecture.md)
- [ROS 2 interface](docs/ros_interface.md)
- [Camera housekeeping registers](docs/camera_housekeeping_registers.md)
- [Hardware](docs/hardware.md)
- [Troubleshooting](docs/troubleshooting.md)

## License

Software in this repository is licensed under the Apache License 2.0 unless stated otherwise.
