# Architecture

This document describes the architecture of the BeagleV-Fire SpaceWire demonstrator and the path followed by commands, diagnostics and camera images through the system.

# 1. System Overview

The demonstrator consists of three main parts:

1. a PC running the graphical user interface and ROS 2 monitoring;
2. a main BeagleV-Fire running the ROS 2 SpaceWire gateway;
3. a second BeagleV-Fire implementing an FPGA mock camera.

```text
PC
│
│ ROS 2 / DDS over Ethernet
│
▼
Main BeagleV-Fire
│
│ SpaceWire
│
▼
Mock-camera BeagleV-Fire
```

The PC does not access the FPGA hardware directly. All hardware access is handled by the main BeagleV-Fire.

---

# 2. PC

The PC runs:

- ROS 2 Jazzy;
- the PySide6 SpaceWire GUI;
- the ROS 2 diagnostic aggregator.

The GUI provides controls for:

- connecting and disconnecting the SpaceWire link;
- selecting an image pattern;
- requesting an image;
- displaying received images;
- monitoring SpaceWire status and errors.

The GUI communicates only through ROS 2 interfaces.

The PC-side launch environment is stored under:

```text
pc/ros2_ws/
```

The GUI is stored under:

```text
pc/gui/
```

---

# 3. Main BeagleV-Fire

The main BeagleV-Fire provides the bridge between ROS 2 and the FPGA SpaceWire implementation.

The software is divided into several layers:

```text
ROS 2
 │
 ▼
gateway.py
 │
 ▼
hardware abstraction
 │
 ▼
beaglev.py
 │
 ▼
low-level SpaceWire / DMA access
 │
 ▼
FPGA
```

## 3.1 ROS 2 Gateway

`gateway.py` implements the ROS-facing part of the system.

It provides:

- SpaceWire connect and disconnect services;
- camera image request service;
- image publication;
- diagnostic publication;
- image-pattern parameter handling.

The gateway itself does not contain direct APB or DMA implementation details.

Instead, it communicates through a hardware abstraction layer.

This allows the same ROS gateway to work with either:

- the real BeagleV-Fire hardware backend;
- a software mock backend.

---

# 4. Hardware Abstraction

The hardware interface is defined in:

```text
spacewire_gateway/hardware/base.py
```

Two implementations are provided:

```text
mock.py
beaglev.py
```

`mock.py` provides a software-only backend that can be used without FPGA hardware.

`beaglev.py` implements the real BeagleV-Fire backend.

The real backend translates generic operations such as:

```text
connect
disconnect
get_status
request_image
poll_image
```

into operations on the SpaceWire FPGA core and DMA controller.

---

# 5. Low-Level Hardware Access

The lowest software layer is stored under:

```text
spacewire_gateway/hardware/lowlevel/
```

The main files are:

```text
spw_debug_devmem2.py
spacewire.py
devmem2_access.py
acces_layer.py
```

These files provide access to the FPGA registers and DMA functionality.

The processor accesses memory-mapped FPGA registers. The SoC interconnect converts these processor accesses into transactions toward the FPGA peripheral.

The software therefore performs memory-mapped register reads and writes rather than manually generating APB signals.

---

# 6. SpaceWire Link Control

A GUI connect request follows this path:

```text
GUI
 │
 │ ROS 2 service
 ▼
spacewire_gateway
 │
 ▼
beaglev.py
 │
 ▼
low-level register access
 │
 ▼
FPGA SpaceWire core
```

The FPGA core is instructed to start the SpaceWire link.

The gateway then reads the SpaceWire status registers and verifies that the link reaches the running state.

Disconnect follows the same path in the opposite control direction.

---

# 7. Camera Request Path

The GUI first selects an image pattern using the `pattern` parameter of the gateway.

When the user requests an image:

```text
GUI
 │
 │ /spacewire/camera/request_image
 ▼
gateway.py
 │
 ▼
beaglev.py
 │
 ├── prepare DMA receiver
 │
 └── transmit camera command
        │
        ▼
     SpaceWire
        │
        ▼
 Mock-camera FPGA
```

The real backend first prepares the DMA receiver and then transmits a SpaceWire command to the mock camera.

The camera command contains the selected image-pattern identifier.

---

# 8. Mock Camera

The mock-camera BeagleV-Fire does not run a ROS application during normal operation.

The camera functionality is implemented in FPGA logic.

It receives commands over SpaceWire, generates the selected 64 × 64 RGB test image and transmits the image back over the SpaceWire link.

Several generated image patterns are available, including solid colours, colour bars, grids and gradients.

---

# 9. Image Receive Path

Large image data is not transferred byte-by-byte through the APB register interface.

Instead, the FPGA receives the SpaceWire packet and transfers the incoming data through DMA into DDR memory.

The receive path is:

```text
Mock-camera FPGA
 │
 │ SpaceWire
 ▼
Main FPGA SpaceWire receiver
 │
 ▼
AXI Stream
 │
 ▼
DMA
 │
 ▼
DDR memory
 │
 ▼
beaglev.py
 │
 ▼
gateway.py
 │
 │ sensor_msgs/Image
 ▼
ROS 2
 │
 ▼
PC GUI
```

After DMA completion, the software reads the received packet from memory.

The packet is checked and converted into an internal image representation.

The ROS gateway then publishes it as:

```text
sensor_msgs/msg/Image
```

using RGB8 encoding.

The GUI subscribes to this topic and displays the image.

---

# 10. Diagnostics

The gateway periodically reads the SpaceWire status and error registers.

It publishes these values as ROS 2 diagnostics:

```text
Main BeagleV-Fire
 │
 ▼
/spacewire/diagnostics
 │
 │ DDS / Ethernet
 ▼
PC
 │
 ▼
diagnostic_aggregator
 │
 ├── /spacewire/diagnostics_agg
 └── /spacewire/diagnostics_toplevel_state
```

The diagnostic information includes the link state and SpaceWire protocol errors.

The diagnostic aggregator is a monitoring component and is not required for the SpaceWire data transfer itself.

---

# 11. Separation of Responsibilities

The main software components have deliberately separate responsibilities:

| Component | Responsibility |
|---|---|
| GUI | User interaction and image display |
| ROS 2 | Communication between PC and board |
| `gateway.py` | ROS 2 interface and hardware-independent logic |
| `base.py` | Hardware interface definition |
| `beaglev.py` | Real SpaceWire and DMA operations |
| low-level modules | Register, memory and DMA access |
| main FPGA | SpaceWire communication and DMA interface |
| mock-camera FPGA | Camera command handling and image generation |

This separation keeps the ROS interface independent from the implementation details of the FPGA hardware.

---

# 12. Repository Locations

The relevant implementation files are located under:

```text
board/ros2_ws/src/spacewire_gateway/
pc/ros2_ws/src/spacewire_pc/
pc/gui/
board/gateware/
```

For the exact ROS 2 topics, services and parameters, see [ros_interface.md](ros_interface.md).

For board and FPGA details, see [hardware.md](hardware.md).
