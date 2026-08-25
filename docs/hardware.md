# Hardware

This document describes the hardware used by the BeagleV-Fire SpaceWire demonstrator.

The system uses two BeagleV-Fire boards:

1. a main board containing the SpaceWire interface used by ROS 2;
2. a second board implementing an FPGA mock camera.

The boards communicate through a physical SpaceWire link.

# 1. Hardware Overview

```text
PC
 │
 │ Ethernet
 ▼
Main BeagleV-Fire
├── RISC-V Linux / ROS 2
├── SpaceWire FPGA core
├── DMA receiver
└── SpaceWire physical interface
        │
        │ SpaceWire
        ▼
Mock-camera BeagleV-Fire
└── FPGA camera emulator
```

The main board handles the connection between the processor and the SpaceWire hardware.

The mock-camera board operates primarily as an FPGA endpoint and does not require a userspace application during normal operation.

---

# 2. BeagleV-Fire Platform

The demonstrator uses the BeagleV-Fire development board based on the Microchip PolarFire SoC.

The device combines:

- a RISC-V processor subsystem;
- programmable FPGA fabric;
- processor-to-FPGA interconnects;
- external DDR memory.

The Linux application runs on the processor subsystem while the SpaceWire implementation runs in the FPGA fabric.

---

# 3. Main BeagleV-Fire

The main board contains:

- the SpaceWire FPGA core;
- a processor-accessible register interface;
- SpaceWire transmit and receive logic;
- DMA support for received packets;
- the physical SpaceWire connection.

The processor controls the SpaceWire core using memory-mapped registers.

The SpaceWire peripheral is mapped at:

```text
0x45000000
```

---

# 4. SpaceWire Register Map

The main FPGA exposes the following registers.

| Offset | Register |
|---:|---|
| `0x00` | CONTROL |
| `0x04` | STATUS |
| `0x08` | TX_DATA |
| `0x0C` | RX_DATA |
| `0x10` | TX_DIVIDER |
| `0x14` | ERRORS |
| `0x18` | CORE_ID |
| `0x1C` | LED |

The software accesses these registers using memory-mapped processor reads and writes.

These accesses are transported through the SoC interconnect toward the FPGA peripheral.

---

# 5. SpaceWire Status

The STATUS register contains the following bits:

| Bit value | Meaning |
|---:|---|
| `0x01` | STARTED |
| `0x02` | CONNECTING |
| `0x04` | RUNNING |
| `0x08` | TX_READY |
| `0x10` | TX_HALF_FULL |
| `0x20` | RX_VALID |
| `0x40` | RX_HALF_FULL |

A typical healthy disconnected state is:

```text
CONTROL = 0x00000000
STATUS  = 0x00000008
ERRORS  = 0x00000000
```

`0x08` indicates that the transmitter is ready while the SpaceWire link is not running.

A typical connected state is:

```text
CONTROL = 0x00000001
STATUS  = 0x0000000C
ERRORS  = 0x00000000
```

`0x0C` corresponds to:

```text
RUNNING
TX_READY
```

The SpaceWire core identifier is:

```text
0x53505731
```

which corresponds to the ASCII text:

```text
SPW1
```

---

# 6. SpaceWire Errors

The hardware reports protocol error conditions that are exposed through the ROS 2 diagnostics.

The software monitors:

- disconnect errors;
- parity errors;
- escape errors;
- credit errors.

A healthy link normally reports:

```text
ERRORS = 0x00000000
```

---

# 7. DMA Receive Path

Camera images are substantially larger than normal control commands.

They are therefore not transferred to the processor byte-by-byte through the SpaceWire register interface.

Instead, received SpaceWire data is transferred to DDR memory using DMA.

The receive path is:

```text
SpaceWire RX
    │
    ▼
AXI Stream
    │
    ▼
DMA
    │
    ▼
DDR
    │
    ▼
Linux software
```

The relevant DMA addresses used by the demonstrator are:

| Function | Address |
|---|---:|
| DMA status | `0x60000010` |
| DMA mask | `0x60000014` |
| DMA clear | `0x60000018` |
| Stream 0 descriptor register | `0x60000460` |
| Descriptor | `0xC4000000` |
| RX buffer | `0xC4001000` |

The descriptor configuration used for the camera receive operation is:

```text
0x0000000D
```

Before requesting an image, the software prepares the DMA receiver and then sends the camera command.

When the DMA transfer completes, the packet is read from DDR and validated before being published through ROS 2.

---

# 8. Camera Packet

The mock camera sends a 64 × 64 RGB888 image.

The packet consists of:

```text
C1 02 40 40
```

followed by:

```text
12288 RGB bytes
```

and a SpaceWire EOP.

The four-byte header represents the camera packet format used by this demonstrator.

The RGB payload size is:

```text
64 × 64 × 3 = 12288 bytes
```

The complete packet processed by the DMA receiver therefore contains:

```text
12292 bytes
```

before the SpaceWire packet termination handling.

---

# 9. Mock-Camera Command Protocol

The mock-camera FPGA accepts a small command protocol over SpaceWire.

The implemented commands are:

| Command | Data |
|---|---|
| START_FRAME | `01 EOP` |
| ABORT_FRAME | `02 EOP` |
| SET_PATTERN | `10 PP EOP` |
| SET_BAYER | `11 BB EOP` |
| CONFIGURE_AND_START | `12 PP BB EOP` |
| RESET_CONFIGURATION | `20 EOP` |
| GET_HOUSEKEEPING | `30 EOP` |

`PP` is the image-pattern identifier.

`BB` is the Bayer/configuration value.

The demonstrator uses the combined command:

```text
12 PP 00 EOP
```

to configure the requested pattern and start an image transfer.

`GET_HOUSEKEEPING` (`30 EOP`) returns the complete 256-byte camera register window. The packet format, register map and decoded meanings are documented in [camera_housekeeping_registers.md](camera_housekeeping_registers.md).

---

# 10. Image Patterns

The mock-camera FPGA implements eight test patterns.

| ID | Pattern |
|---:|---|
| 0 | Color boxes / grid |
| 1 | Solid red |
| 2 | Solid green |
| 3 | Solid blue |
| 4 | Vertical color bars |
| 5 | Horizontal color bars |
| 6 | Horizontal black-to-white gradient |
| 7 | Vertical black-to-white gradient |

The pattern is selected through the ROS 2 `pattern` parameter and included in the SpaceWire camera command.

---

# 11. DMA Recovery

The DMA controller can require recovery after an error.

The hardware implementation therefore includes a DMA reset mechanism.

The real hardware backend tracks whether an image request is in progress.

If the image transfer encounters an error or timeout, the software can:

1. reset or recover the DMA receiver;
2. prepare a new receive descriptor;
3. retransmit the same camera command;
4. retry the request a bounded number of times.

This allows the gateway to recover from transient DMA receive failures without restarting the complete ROS 2 application.

---

# 12. FPGA Gateware

The repository includes the final programmed gateware for both boards.

## Main board

```text
board/gateware/main_board/
├── dma_reset.spi
└── mpfs_dtbo.spi
```

`dma_reset.spi` contains the final main-board design used by the ROS 2 gateway.

## Mock-camera board

```text
board/gateware/mock_camera/
├── mock_camera.spi
└── mpfs_dtbo.spi
```

`mock_camera.spi` contains the final FPGA camera emulator.

The programming scripts are:

```text
board/scripts/program_main_board.sh
board/scripts/program_mock_camera.sh
```

See [installation.md](installation.md) for the programming procedure.

---

# 13. SpaceWire Interface PCB

The project also includes a custom PCB for interfacing the BeagleV-Fire connector with the differential SpaceWire signals.

The KiCad project is stored under:

```text
hardware/connector_board/
```

The PCB contains:

- BeagleV-Fire board connector;
- differential SpaceWire transmit interface;
- differential SpaceWire receive interface;
- voltage-level translation;
- Micro-D SpaceWire connector;
- decoupling and supporting passive components.

The final design uses a four-layer PCB.

The primary active components include:

| Function | Component |
|---|---|
| LVDS transmitter | DS90LV027ATM/NOPB |
| LVDS receiver | DS90LV028ATM/NOPB |
| Level translator | SN74AVC2T45 |
| Board connector | Samtec QTH-020 series |
| SpaceWire connector | 9-pin Micro-D |

The repository contains:

```text
3D/             Component 3D models
footprints/     Custom KiCad footprints
symbols/        Custom KiCad symbols
fabrication/    Final fabrication files
final-review/   PCB review plots
```

The final manufacturer-ready Gerber and drill archive is:

```text
hardware/connector_board/fabrication/PCB.zip
```

---

# 14. Standalone Hardware Debugger

Standalone hardware access utilities are included under:

```text
board/debug/spw_py/
```

These tools can be used to inspect the SpaceWire core independently of ROS 2.

The same low-level hardware concepts are also used by the real ROS hardware backend.

The debug tools are particularly useful during:

- FPGA bring-up;
- register inspection;
- SpaceWire link testing;
- DMA debugging;
- camera packet testing.

---

# 15. Software and Hardware Boundary

The important boundary in the implementation is:

```text
gateway.py
    │
    ▼
beaglev.py
    │
    ▼
low-level hardware access
    │
    ▼
FPGA
```

`gateway.py` is responsible for ROS 2.

`beaglev.py` converts generic operations into SpaceWire and DMA operations.

The low-level modules perform memory-mapped register and memory access.

Large camera payloads use the DMA path rather than the processor-accessible SpaceWire register interface.

For the complete software data flow, see [architecture.md](architecture.md).
