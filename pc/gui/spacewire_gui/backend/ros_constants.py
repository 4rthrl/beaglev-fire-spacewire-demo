"""ROS topic, service, and parameter names for the SpaceWire gateway."""

DIAGNOSTICS_TOPIC = "/diagnostics"
CAMERA_IMAGE_TOPIC = "/camera/image"

CONNECT_SERVICE = "/spacewire/connect"
DISCONNECT_SERVICE = "/spacewire/disconnect"
REQUEST_IMAGE_SERVICE = "/camera/request_image"

GATEWAY_NODE = "/spacewire_gateway"
PATTERN_PARAMETER = "pattern"

DIAGNOSTIC_STATUS_NAME = "SpaceWire Link"
GUI_NODE_NAME = "spacewire_gui"

SPIN_INTERVAL_MS = 20
IMAGE_REQUEST_TIMEOUT_MS = 5000
THREAD_JOIN_TIMEOUT_MS = 3000
