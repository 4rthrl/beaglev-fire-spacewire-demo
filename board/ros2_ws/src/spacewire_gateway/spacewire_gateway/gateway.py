from diagnostic_msgs.msg import DiagnosticArray
from diagnostic_msgs.msg import DiagnosticStatus
from diagnostic_msgs.msg import KeyValue
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from spacewire_gateway.hardware import create_hardware
from std_srvs.srv import Trigger


class SpaceWireGateway(Node):

    def __init__(self):
        super().__init__('spacewire_gateway')

        # Camera pattern parameter — FPGA pattern IDs 0..7
        # See hardware/mock.py and hardware/beaglev.py for the pattern mapping.
        self.declare_parameter('pattern', 1)
        self.declare_parameter('hardware_backend', 'mock')

        backend = self.get_parameter('hardware_backend').value
        self._hardware = create_hardware(backend)
        self._hardware_backend = backend

        # --------------------------------------------------------------
        # Publishers
        # --------------------------------------------------------------
        self.diagnostics_pub = self.create_publisher(
            DiagnosticArray,
            '/diagnostics',
            10
        )

        self.image_pub = self.create_publisher(
            Image,
            '/camera/image',
            10
        )

        # --------------------------------------------------------------
        # Services
        # --------------------------------------------------------------
        self.connect_service = self.create_service(
            Trigger,
            '/spacewire/connect',
            self.connect_callback
        )

        self.disconnect_service = self.create_service(
            Trigger,
            '/spacewire/disconnect',
            self.disconnect_callback
        )

        self.request_image_service = self.create_service(
            Trigger,
            '/camera/request_image',
            self.request_image_callback
        )

        # --------------------------------------------------------------
        # Timers
        # --------------------------------------------------------------
        self.diagnostics_timer = self.create_timer(
            1.0,
            self.publish_diagnostics
        )

        self.image_poll_timer = self.create_timer(
            0.02,
            self.poll_image_callback
        )

        self.get_logger().info('SpaceWire Gateway started')
        self.get_logger().info(f'Hardware backend: {backend}')
        self.get_logger().info(
            f'Initial image pattern: '
            f'{self.get_parameter("pattern").value}'
        )

    # ------------------------------------------------------------------
    # Connect
    # ------------------------------------------------------------------
    def connect_callback(self, request, response):
        self.get_logger().info('Connect requested')

        success, message = self._hardware.connect()

        if success:
            self.get_logger().info(message)
        else:
            self.get_logger().error(message)

        response.success = success
        response.message = message
        return response

    # ------------------------------------------------------------------
    # Disconnect
    # ------------------------------------------------------------------
    def disconnect_callback(self, request, response):
        self.get_logger().info('Disconnect requested')

        success, message = self._hardware.disconnect()

        if success:
            self.get_logger().info(message)
        else:
            self.get_logger().error(message)

        response.success = success
        response.message = message
        return response

    # ------------------------------------------------------------------
    # Request image
    # ------------------------------------------------------------------
    def request_image_callback(self, request, response):
        pattern = self.get_parameter('pattern').value

        self.get_logger().info(
            f'Image request received, pattern={pattern}'
        )

        success, message = self._hardware.request_image(pattern)

        if success:
            self.get_logger().info(message)
        else:
            self.get_logger().error(message)

        response.success = success
        response.message = message
        return response

    # ------------------------------------------------------------------
    # Poll image
    # ------------------------------------------------------------------
    def poll_image_callback(self):
        received = self._hardware.poll_image()
        if received is None:
            return

        msg = Image()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera'
        msg.height = received.height
        msg.width = received.width
        msg.encoding = received.encoding
        msg.is_bigendian = 0
        msg.step = received.step
        msg.data = list(received.data)

        self.image_pub.publish(msg)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    def publish_diagnostics(self):
        status = self._hardware.get_status()

        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()

        diag = DiagnosticStatus()
        diag.name = 'SpaceWire Link'

        if self._hardware_backend == 'beaglev':
            diag.hardware_id = 'beaglev-spacewire'
        else:
            diag.hardware_id = 'mock-spacewire'

        has_error = (
            status.disconnect_error
            or status.parity_error
            or status.escape_error
            or status.credit_error
        )

        if has_error:
            diag.level = DiagnosticStatus.ERROR
            diag.message = 'SpaceWire errors detected'

        elif status.running:
            diag.level = DiagnosticStatus.OK
            diag.message = 'SpaceWire link running'

        elif status.connecting:
            diag.level = DiagnosticStatus.WARN
            diag.message = 'SpaceWire link connecting'

        else:
            diag.level = DiagnosticStatus.WARN
            diag.message = 'SpaceWire link disconnected'

        diag.values = [
            KeyValue(key='started', value=str(status.started)),
            KeyValue(key='connecting', value=str(status.connecting)),
            KeyValue(key='running', value=str(status.running)),
            KeyValue(key='tx_ready', value=str(status.tx_ready)),
            KeyValue(key='tx_half_full', value=str(status.tx_half_full)),
            KeyValue(key='rx_valid', value=str(status.rx_valid)),
            KeyValue(key='rx_half_full', value=str(status.rx_half_full)),
            KeyValue(
                key='disconnect_error',
                value=str(status.disconnect_error),
            ),
            KeyValue(
                key='parity_error',
                value=str(status.parity_error),
            ),
            KeyValue(
                key='escape_error',
                value=str(status.escape_error),
            ),
            KeyValue(
                key='credit_error',
                value=str(status.credit_error),
            ),
            KeyValue(key='tx_divider', value=str(status.tx_divider)),
            KeyValue(
                key='control_raw',
                value=f'0x{status.control_raw:08X}',
            ),
            KeyValue(
                key='status_raw',
                value=f'0x{status.status_raw:08X}',
            ),
            KeyValue(
                key='errors_raw',
                value=f'0x{status.errors_raw:08X}',
            ),
            KeyValue(
                key='core_id',
                value=f'0x{status.core_id:08X}',
            ),
        ]

        msg.status.append(diag)
        self.diagnostics_pub.publish(msg)


def main(args=None):

    rclpy.init(args=args)

    node = SpaceWireGateway()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node._hardware.shutdown()
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
