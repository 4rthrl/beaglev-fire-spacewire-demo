# SpaceWire Camera Control

Desktop GUI for controlling a SpaceWire camera system. The application targets a
BeagleV-Fire gateway running ROS 2, but ships with a mock backend so it can be
developed on Windows or Linux without ROS installed.

## Architecture

```
PC GUI (PySide6)
    ↓  backend API (Qt signals)
MockSpaceWireBackend  |  RosSpaceWireBackend
    ↓
BeagleV-Fire / FPGA / SpaceWire / mock camera
```

The GUI never talks to hardware or ROS directly. It depends only on
`SpaceWireBackend` signals and methods. The ROS backend runs `rclpy` on a
dedicated worker thread and translates ROS messages into the existing
`SpaceWireStatus` and `QImage` models.

## Requirements

- Python 3.10+
- Windows or Linux

### ROS backend (Ubuntu 24.04 + ROS 2 Jazzy)

- `ros-jazzy-rclpy`
- `ros-jazzy-std-srvs`
- `ros-jazzy-sensor-msgs`
- `ros-jazzy-diagnostic-msgs`

## Setup (Windows)

From the project root (`gui-space/`):

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m spacewire_gui
```

Alternative launcher:

```powershell
python main.py
```

## Setup (Ubuntu 24.04 + ROS 2 Jazzy)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
source /opt/ros/jazzy/setup.bash
python3 -m spacewire_gui --backend ros
```

Ensure `/spacewire_gateway` is running before starting the ROS backend.

## Usage

On Linux, use `python3`. On Windows, use `python`.

### Mock backend (default)

```bash
python3 -m spacewire_gui
# or
python3 -m spacewire_gui --backend mock
```

1. Launch the application — status bar shows **Mock backend active**.
2. Click **Connect** — link transitions through Connecting to Connected.
3. Request test images with **Solid Red**, **Gradient**, or **Checkerboard**.
4. Click **Refresh Housekeeping** to fetch one camera register snapshot, then browse groups or search a field. Selection uses the cached snapshot and does not send another SpaceWire request.
5. Click **Disconnect** to return to the idle state.
6. Open **View → Event Log** to show or hide the event log (visible by default).
7. Open **View → Simulation / Debug** to inject fault conditions (mock only).

### ROS backend

```bash
python3 -m spacewire_gui --backend ros
# or
SPACEWIRE_BACKEND=ros python3 -m spacewire_gui
```

1. Status bar shows **ROS backend active**.
2. Link status updates arrive from `/diagnostics`.
3. **Connect** / **Disconnect** call `/spacewire/connect` and `/spacewire/disconnect`.
4. Pattern buttons set the gateway `pattern` parameter, then call `/camera/request_image`.
5. Images arrive on `/camera/image` and display at their native resolution.
6. **Refresh Housekeeping** calls `/camera/get_housekeeping` and displays the snapshot published on `/camera/housekeeping`.
7. Open **View → Event Log** to show or hide the event log.

The normal demonstrator startup (`./pc/start_pc.sh`, which launches `spacewire_pc.launch.py`) applies the matching remaps to `/spacewire/camera/get_housekeeping` and `/spacewire/camera/housekeeping`. Manual remaps are not required when using that launch file. The board launch file `spacewire_gateway.launch.py` performs the corresponding gateway remaps.

## Project structure

```
gui-space/
├── main.py                     # root launcher
├── requirements.txt
├── requirements-ros.txt        # ROS setup notes
├── README.md
└── spacewire_gui/
    ├── main.py                 # QApplication entry
    ├── backend/
    │   ├── base.py             # abstract backend API
    │   ├── mock_backend.py     # offline simulation
    │   ├── ros_backend.py      # ROS GUI-thread relay
    │   ├── ros_worker.py       # rclpy worker on QThread
    │   ├── ros_image.py        # sensor_msgs/Image → QImage
    │   ├── ros_constants.py    # topic/service names
    │   └── test_patterns.py    # deterministic 64×64 TPG generators
    ├── gui/
    │   ├── main_window.py
    │   ├── styles.py
    │   └── widgets/
    └── models/
        ├── spacewire_status.py
        ├── diagnostics_mapping.py
        ├── housekeeping.py
        ├── housekeeping_mapping.py
        ├── housekeeping_display.py
        └── image_patterns.py
```

## Status fields

| Field | Type | Description |
|---|---|---|
| `started` | bool | Link start requested |
| `connecting` | bool | Connection in progress |
| `running` | bool | Link running |
| `tx_ready` | bool | TX ready |
| `tx_half_full` | bool | TX FIFO half full |
| `rx_valid` | bool | RX data valid |
| `rx_half_full` | bool | RX FIFO half full |
| `disconnect_error` | bool | Disconnect error |
| `parity_error` | bool | Parity error |
| `escape_error` | bool | Escape error |
| `credit_error` | bool | Credit error |
| `tx_divider` | int | TX clock divider |
| `control_raw` | int | Control register (hex in GUI) |
| `status_raw` | int | Status register (hex in GUI) |
| `errors_raw` | int | Errors register (hex in GUI) |
| `core_id` | int | Core ID (hex in GUI) |

Link connection state and error/health state are separate. A parity error does
not disconnect the link; the summary may read **Connected — Error detected**.

Status updates are translated from a `DiagnosticStatus` named **SpaceWire Link**
on `/diagnostics` into `SpaceWireStatus` before reaching the GUI widgets.

## ROS backend API

| Action | ROS interface |
|---|---|
| Status | Subscribe `/diagnostics` (`diagnostic_msgs/DiagnosticArray`) |
| Connect | Service `/spacewire/connect` (`std_srvs/Trigger`) |
| Disconnect | Service `/spacewire/disconnect` (`std_srvs/Trigger`) |
| Set pattern | Parameter `pattern` on `/spacewire_gateway` (`0`–`7`) |
| Request image | Service `/camera/request_image` (`std_srvs/Trigger`) |
| Receive image | Subscribe `/camera/image` (`sensor_msgs/Image`, `rgb8`) |
| Request housekeeping | Service `/camera/get_housekeeping` (`std_srvs/Trigger`) |
| Receive housekeeping | Subscribe `/camera/housekeeping` (`diagnostic_msgs/DiagnosticArray`) |

The Camera Housekeeping panel shows:

- **Refresh Housekeeping** and request success/failure;
- a persistent camera summary (ID, firmware, mode, source, pattern, image size, TC/frame counters, error/monitor/SpaceWire indicators);
- a grouped register inspector with field search;
- decoded values (for example `StandBy [1]`, `Generated Patterns [3]`, `64 × 64`);
- **Not supported** for BIST when the capability is false, and **Unavailable** for invalid monitor channels.

One housekeeping service call retrieves one coherent 256-byte camera register snapshot. The GUI stores that snapshot and lets the operator browse groups and fields locally. It does not call additional per-register services.

The public namespaced interface (via launch remapping) is `/spacewire/camera/get_housekeeping` and `/spacewire/camera/housekeeping`. Both the GUI mock backend and the ROS / BeagleV-Fire backend support housekeeping.

The register protocol and FPGA field meanings are documented in [camera_housekeeping_registers.md](../../docs/camera_housekeeping_registers.md).

Pattern values:

| Value | Pattern |
|---|---|
| 0 | Color Boxes / Grid |
| 1 | Solid Red |
| 2 | Solid Green |
| 3 | Solid Blue |
| 4 | Vertical Color Bars |
| 5 | Horizontal Color Bars |
| 6 | Horizontal Black-to-White Gradient |
| 7 | Vertical Black-to-White Gradient |

`rclpy` runs on a `QThread` worker. ROS callbacks emit Qt signals to the GUI
thread. See `backend/base.py` and `backend/ros_worker.py` for the threading layout.

## Test pattern generators

Mock images are generated in `backend/test_patterns.py` as deterministic 64×64
patterns. The ROS backend displays images at the resolution published on
`/camera/image`.
