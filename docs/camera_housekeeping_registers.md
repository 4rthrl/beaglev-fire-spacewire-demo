# Camera Housekeeping Registers

This document is the central reference for the mock-camera housekeeping interface used by the FPGA, ROS gateway and PC GUI.

It describes the SpaceWire protocol, the 256-byte register window, the ROS representation and how the GUI presents decoded values.

Do not treat this as a source of physical engineering units. Where a field has no defined scaling, only the raw register value is meaningful.

For the public ROS names and launch remapping, see [ros_interface.md](ros_interface.md).

---

# 1. Protocol

## Command

Housekeeping is requested with a single SpaceWire telecommand:

```text
30 EOP
```

`GET_HOUSEKEEPING` is a valid telecommand. It increments `TC_COUNTER`. The snapshot returned for that request already contains this increment.

There is no separate SpaceWire command for reading one individual register. The complete register window is returned in one response.

## Response

The response contains exactly 260 DATA bytes, followed by SpaceWire EOP:

```text
C1 F0 00 40
<256-byte register window>
EOP
```

| Field | Size | Description |
|---|---|---|
| `C1 F0 00 40` | 4 bytes | Housekeeping response header (not part of the register bank) |
| Register window | 256 bytes | 64 × 32-bit words, big-endian |
| EOP | — | SpaceWire end of packet |

The 256-byte window is a fixed size. Unused locations are reserved so future fields can be added without changing the packet length.

The ROS gateway and PC GUI store this as one coherent snapshot. Browsing groups or fields in the GUI does not generate another camera request.

---

# 2. Register map

Offsets are byte offsets into the 256-byte window. Each register is one 32-bit big-endian word unless noted.

## 2.1 Identification

| Offset | Register | Relevant bits | Meaning / GUI interpretation |
|---|---|---|---|
| `0x00` | `DEVICE_ID` | `[31:0]` | Camera identifier. Current hardware: `0x43414D31` (ASCII `CAM1`) |
| `0x04` | `DESTINATION_ADDRESS` | `[7:0]` | Destination address. Current implementation uses `0` |
| `0x08` | `PROTOCOL_ID` | `[7:0]` | Protocol identifier. Current value: `1` |
| `0x0C` | `PROTOCOL_VERSION` | `[23:16]` major, `[15:8]` minor, `[7:0]` patch; `[31:24]` unused | Version text `major.minor.patch`. `0x00010000` → `1.0.0` |
| `0x10` | `FW_VERSION` | same packing as `PROTOCOL_VERSION` | Firmware version text |
| `0x14` | `REGISTER_MAP_VERSION` | same packing as `PROTOCOL_VERSION` | Register-map version text |
| `0x18` | `CAPABILITIES` | `[7:0]` capability flags | Advertised features (see below). Raw value also shown |
| `0x1C` | Reserved | — | Unused |

### Capabilities `[7:0]`

| Bit | Meaning |
|---:|---|
| 0 | Generated Patterns |
| 1 | BIST |
| 2 | Monitor Values |
| 3 | Integration Time |
| 4 | Image Corrections |
| 5 | Stored Patterns |
| 6 | Logical Address |
| 7 | Bayer |

Current hardware reports `0x00000081`: Generated Patterns and Bayer are advertised.

## 2.2 Camera state

| Offset | Register | Relevant bits | Meaning / GUI interpretation |
|---|---|---|---|
| `0x20` | `BIST_STATUS` | `[15:8]` error code, `[7]` failed, `[6:0]` test ID | Decoded only when BIST is supported (capability bit 1). See note below |
| `0x24` | `OPERATING_MODE` | `[3:0]` | `0` Starting Up, `1` StandBy, `2` Service, `3` Multiple Imaging, `4` Single Imaging, `5` Maintenance. GUI: `StandBy [1]` |
| `0x28` | `IMAGE_SOURCE` | `[3:0]` | `0` None, `1` Image Sensor, `2` Stored Patterns, `3` Generated Patterns. GUI: `Generated Patterns [3]` |
| `0x2C` | `PATTERN` | `[2:0]` | Selected generated pattern `0..7` (see [Pattern identifiers](#23-pattern-identifiers)) |
| `0x30` | `BAYER` | `[1:0]` | Bayer pattern code. This field is reported; it is not documented here as changing the demonstrator's RGB output |
| `0x34` | `CAMERA_STATUS` | bit 0 `frame_active`, bit 1 `bist_running`, bit 2 `error_present` | Frame / BIST-running / error flags. Error drives the Camera Error indicator |
| `0x38` | `LAST_ERROR` | `[15:0]` | Last error code |
| `0x3C` | Reserved | — | Unused |

`IMAGE_SOURCE` and `PATTERN` are intentionally separate registers: source selects Generated Patterns, stored patterns or the sensor; `PATTERN` selects which generated pattern is active.

### BIST

BIST is **not implemented** on the current hardware. Capability bit 1 is `0`.

A raw `BIST_STATUS` of `0` must not be treated as “BIST passed”. The fields are zero while BIST is unsupported. The GUI shows **Not supported**.

Interpret `failed`, test ID and error code as meaningful BIST results only when capability bit 1 is set.

## 2.3 Pattern identifiers

`PATTERN[2:0]` uses the same identifiers as the gateway `pattern` parameter and `pc/gui/spacewire_gui/models/image_patterns.py`:

| Value | Pattern |
|---:|---|
| 0 | Color Boxes / Grid |
| 1 | Solid Red |
| 2 | Solid Green |
| 3 | Solid Blue |
| 4 | Vertical Color Bars |
| 5 | Horizontal Color Bars |
| 6 | Horizontal Black-to-White Gradient |
| 7 | Vertical Black-to-White Gradient |

## 2.4 Image configuration

| Offset | Register | Relevant bits | Meaning / GUI interpretation |
|---|---|---|---|
| `0x40` | `INTEGRATION_TIME` | `[31:0]` | Integration time in microseconds. Not currently advertised by `CAPABILITIES` |
| `0x44` | `LUP_CONFIG` | bit 7 enable, `[6:0]` threshold | GUI: Enabled / Disabled and threshold; raw register also available |
| `0x48` | `IMAGE_CORRECTIONS` | `[7:6]` PLR, `[5:4]` corner, `[3]` binning, `[2]` gain, `[1]` offset, `[0]` bad pixel | Named correction flags. Corner: `0` Upper Left, `1` Upper Right, `2` Lower Left, `3` Lower Right |
| `0x4C` | `NUC_LUT_VERSION` | `[7:0]` | LUT version / value |
| `0x50` | `BP_LUT_VERSION` | `[7:0]` | LUT version / value |
| `0x54` | `TEST_PATTERN_A_VERSION` | `[7:0]` | Version / value |
| `0x58` | `TEST_PATTERN_B_VERSION` | `[7:0]` | Version / value |
| `0x5C` | `IMAGE_SIZE` | `[31:16]` height, `[15:0]` width | GUI primary display `width × height`. Example: `0x00400040` → `64 × 64` |

Do not reverse width and height.

## 2.5 Command and frame counters

| Offset | Register | Relevant bits | Meaning / GUI interpretation |
|---|---|---|---|
| `0x60` | `TC_COUNTER` | `[31:0]` | Telecommand counter. Incremented by `GET_HOUSEKEEPING` itself |
| `0x64` | `LAST_TC_ID` | `[7:0]` | Last telecommand ID |
| `0x68` | `LAST_TC_STATUS` | bit 0 ACK, bit 1 Data error, bit 2 ID error, bit 3 Length error, bit 4 CRC error | Named TC status flags; raw register also available |
| `0x6C` | `FRAME_COUNTER` | `[31:0]` | Frame counter |
| `0x70` | `ABORT_COUNTER` | `[31:0]` | Abort counter |
| `0x74` | `COMMAND_ERROR_COUNTER` | `[31:0]` | Command error counter |
| `0x78` | `UPTIME_SECONDS` | `[31:0]` | Uptime in seconds |
| `0x7C` | Reserved | — | Unused |

## 2.6 Monitor bank

| Offset | Register | Relevant bits | Meaning / GUI interpretation |
|---|---|---|---|
| `0x80` | `MONITOR_VALID` | bits `[8:0]` validity bitmap | Which monitor channels are valid (see below) |
| `0x84` | `TEMP_DETECTOR` | `[31:0]` | Detector temperature **raw**. Software treats this as signed 32-bit. No physical scaling is defined |
| `0x88` | `VDD20_VOLTAGE` | `[31:0]` | VDD 2.0 V **raw** |
| `0x8C` | `CORE_1V2_CURRENT` | `[31:0]` | Core 1.2 V current **raw** |
| `0x90` | `CORE_1V2_VOLTAGE` | `[31:0]` | Core 1.2 V **raw** |
| `0x94` | `IO_3V3_CURRENT` | `[31:0]` | I/O 3.3 V current **raw** |
| `0x98` | `IO_3V3_VOLTAGE` | `[31:0]` | I/O 3.3 V **raw** |
| `0x9C` | `INPUT_5V_CURRENT` | `[31:0]` | Input 5 V current **raw** |
| `0xA0` | `TEMP_FPGA` | `[31:0]` | FPGA temperature **raw**. Software treats this as signed 32-bit. No physical scaling is defined |
| `0xA4` | `TEMP_POWER` | `[31:0]` | Power temperature **raw**. Software treats this as signed 32-bit. No physical scaling is defined |
| `0xA8`–`0xBF` | Reserved | — | Unused |

### `MONITOR_VALID` bits

| Bit | Channel |
|---:|---|
| 0 | Detector temperature |
| 1 | VDD20 voltage |
| 2 | Core 1.2 V current |
| 3 | Core 1.2 V voltage |
| 4 | I/O 3.3 V current |
| 5 | I/O 3.3 V voltage |
| 6 | Input 5 V current |
| 7 | FPGA temperature |
| 8 | Power temperature |

Current hardware returns `MONITOR_VALID = 0`. Monitor registers are placeholders.

**Zero is not a real temperature, current or voltage.** The GUI shows **Unavailable** / invalid. Do not invent millivolts, milliamps, degrees, milli-degrees, offsets or other scaling until a physical mapping is defined. Raw values may appear in the inspector as secondary debug text only.

## 2.7 Camera-side SpaceWire diagnostics

These registers belong to the **mock camera**, not the main BeagleV-Fire gateway SpaceWire core published on `/spacewire/diagnostics`.

| Offset | Register | Relevant bits | Meaning / GUI interpretation |
|---|---|---|---|
| `0xC0` | `SPW_RX_PACKET_COUNTER` | `[31:0]` | Camera RX packet counter |
| `0xC4` | `SPW_TX_PACKET_COUNTER` | `[31:0]` | Camera TX packet counter |
| `0xC8` | `SPW_ERROR_COUNTER` | `[31:0]` | Camera SpaceWire error counter |
| `0xCC` | `LAST_SPW_ERROR` | `[31:0]` | Last camera SpaceWire error |
| `0xD0`–`0xDF` | Reserved | — | Unused |

Current hardware returns zero for these values.

## 2.8 Reserved / expansion

| Offset | Register | Relevant bits | Meaning / GUI interpretation |
|---|---|---|---|
| `0xE0`–`0xFC` | Reserved | — | Unused expansion space |

The last word of the window is at offset `0xFC`. The packet length stays 256 register bytes regardless of how many of these locations are used later.

---

# 3. ROS representation

The gateway decodes the 256-byte window into one `diagnostic_msgs/msg/DiagnosticArray` published on:

```text
/spacewire/camera/housekeeping
```

Acquisition is triggered by:

```text
/spacewire/camera/get_housekeeping
std_srvs/srv/Trigger
```

Internal node names are `/camera/get_housekeeping` and `/camera/housekeeping`. [`spacewire_gateway.launch.py`](../board/ros2_ws/src/spacewire_gateway/launch/spacewire_gateway.launch.py) remaps them to the public `/spacewire/camera/...` names. [`spacewire_pc.launch.py`](../pc/ros2_ws/src/spacewire_pc/launch/spacewire_pc.launch.py) applies the matching GUI remaps. Starting the demonstrator with `./scripts/run_gateway.sh` and `./pc/start_pc.sh` does not require manual remaps.

The array is split into six `DiagnosticStatus` groups:

| Group | Source |
|---|---|
| `Camera/Identification` | Device ID, versions, capabilities |
| `Camera/State` | Mode, source, pattern, camera status, BIST |
| `Camera/Image Configuration` | LUP, corrections, image size, LUT versions |
| `Camera/Counters` | TC / frame / abort / error counters, last TC status |
| `Camera/Monitors` | Validity bitmap and raw monitor channels |
| `Camera/SpaceWire` | Camera-side SpaceWire packet and error counters |

The gateway publishes **decoded fields** (names, flags, version text, width/height) together with selected **raw** registers (for example `capabilities_raw`, `image_size_raw`). The GUI formats those decoded fields; it does not re-decode FPGA bit layouts from the raw window.

---

# 4. GUI representation

The Camera Housekeeping panel stores one snapshot per successful Refresh.

| GUI area | Content |
|---|---|
| Refresh Housekeeping | Calls `/spacewire/camera/get_housekeeping` once |
| Camera Summary | Camera ID, firmware, operating mode, image source, pattern, image size, TC counter, frame counter; Camera Error / Monitors / SpaceWire indicators |
| Inspector | Group combo and field search over the cached snapshot; scrollable decoded label/value rows for the selected group |
| BIST | **Not supported** while capability bit 1 is false |
| Monitors | **Unavailable** when the corresponding `MONITOR_VALID` bit is clear |
| SpaceWire errors | Summary indicator plus inspector counters / last error |

Only **Refresh Housekeeping** generates camera traffic. Group and field selection use the latest received snapshot.

The GUI mock backend and the ROS / BeagleV-Fire backend both implement this same snapshot model.

---

# 5. Current validated baseline

The following is an **example** of values observed on the real mock-camera FPGA over SpaceWire. It is not a specification. Counters and the current pattern are runtime-dependent and are omitted.

| Field | Observed value |
|---|---|
| `DEVICE_ID` | `0x43414D31` (`CAM1`) |
| `DESTINATION_ADDRESS` | `0` |
| `PROTOCOL_ID` | `1` |
| `PROTOCOL_VERSION` | `1.0.0` |
| `FW_VERSION` | `1.0.0` |
| `REGISTER_MAP_VERSION` | `1.0.0` |
| `CAPABILITIES` | `0x00000081` |
| `OPERATING_MODE` | StandBy |
| `IMAGE_SOURCE` | Generated Patterns |
| `IMAGE_SIZE` | 64 × 64 |
| `MONITOR_VALID` | `0` |
