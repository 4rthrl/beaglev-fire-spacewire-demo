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

        self.housekeeping_pub = self.create_publisher(
            DiagnosticArray,
            '/camera/housekeeping',
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

        self.housekeeping_service = self.create_service(
            Trigger,
            '/camera/get_housekeeping',
            self.get_housekeeping_callback
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
    # Camera housekeeping
    # ------------------------------------------------------------------
    def get_housekeeping_callback(self, request, response):
        self.get_logger().info('Housekeeping request received')

        success, message, hk = self._hardware.get_housekeeping()

        if not success or hk is None:
            self.get_logger().error(message)
            response.success = False
            response.message = message
            return response

        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()

        hardware_id = f'camera-0x{hk.device_id:08X}'

        def make_status(name, level, text, values):
            diag = DiagnosticStatus()
            diag.name = name
            diag.hardware_id = hardware_id
            diag.level = level
            diag.message = text
            diag.values = [
                KeyValue(key=key, value=str(value))
                for key, value in values
            ]
            return diag

        identification = make_status(
            'Camera/Identification',
            DiagnosticStatus.OK,
            'Camera identification and versions',
            [
                ('device_id', f'0x{hk.device_id:08X}'),
                (
                    'destination_address',
                    f'0x{hk.destination_address_value:02X}',
                ),
                ('protocol_id', f'0x{hk.protocol_id_value:02X}'),
                ('protocol_version', hk.protocol_version_text),
                ('fw_version', hk.fw_version_text),
                ('register_map_version', hk.register_map_version_text),
                ('capabilities_raw', f'0x{hk.capabilities:08X}'),
                (
                    'cap_generated_patterns',
                    hk.capability_generated_patterns,
                ),
                ('cap_bist', hk.capability_bist),
                ('cap_monitor_values', hk.capability_monitor_values),
                (
                    'cap_integration_time',
                    hk.capability_integration_time,
                ),
                (
                    'cap_image_corrections',
                    hk.capability_image_corrections,
                ),
                ('cap_stored_patterns', hk.capability_stored_patterns),
                ('cap_logical_address', hk.capability_logical_address),
                ('cap_bayer', hk.capability_bayer),
            ],
        )

        state_level = (
            DiagnosticStatus.ERROR
            if hk.error_present
            else DiagnosticStatus.OK
        )

        state = make_status(
            'Camera/State',
            state_level,
            (
                'Camera reports an error'
                if hk.error_present
                else 'Camera state normal'
            ),
            [
                ('operating_mode', hk.operating_mode_name),
                ('operating_mode_code', hk.operating_mode_code),
                ('image_source', hk.image_source_name),
                ('image_source_code', hk.image_source_code),
                ('pattern', hk.pattern_select),
                ('bayer_pattern', hk.bayer_pattern),

                ('frame_active', hk.frame_active),
                ('bist_running', hk.bist_running),
                ('error_present', hk.error_present),
                ('camera_status_raw', f'0x{hk.camera_status:08X}'),
                ('last_error_code', f'0x{hk.last_error_code:04X}'),

                # BIST is decoded, but capability_bist tells clients
                # whether BIST is actually implemented.
                ('bist_supported', hk.capability_bist),
                ('bist_test_id', hk.bist_test_id),
                ('bist_failed', hk.bist_failed),
                ('bist_error_code', f'0x{hk.bist_error_code:02X}'),
                ('bist_status_raw', f'0x{hk.bist_status:08X}'),
            ],
        )

        configuration = make_status(
            'Camera/Image Configuration',
            DiagnosticStatus.OK,
            'Current image configuration',
            [
                ('integration_time_us', hk.integration_time),

                ('lup_enabled', hk.lup_enabled),
                ('lup_threshold', hk.lup_threshold),
                ('lup_raw', f'0x{hk.lup_config:08X}'),

                (
                    'correction_bad_pixel',
                    hk.correction_bad_pixel,
                ),
                ('correction_offset', hk.correction_offset),
                ('correction_gain', hk.correction_gain),
                ('correction_binning', hk.correction_binning),
                (
                    'correction_corner',
                    hk.correction_corner_name,
                ),
                ('correction_corner_code', hk.correction_corner),
                ('correction_plr', hk.correction_plr),
                (
                    'image_corrections_raw',
                    f'0x{hk.image_corrections:08X}',
                ),

                ('nuc_lut_version', hk.nuc_lut_version_value),
                ('bp_lut_version', hk.bp_lut_version_value),
                (
                    'test_pattern_a_version',
                    hk.test_pattern_a_version_value,
                ),
                (
                    'test_pattern_b_version',
                    hk.test_pattern_b_version_value,
                ),

                ('image_width', hk.image_width),
                ('image_height', hk.image_height),
                ('image_size_raw', f'0x{hk.image_size:08X}'),
            ],
        )

        counters = make_status(
            'Camera/Counters',
            DiagnosticStatus.OK,
            'Camera command and frame counters',
            [
                ('tc_counter', hk.tc_counter),
                ('last_tc_id', hk.last_tc_id_value),
                ('tc_ack', hk.tc_ack),
                ('tc_data_error', hk.tc_data_error),
                ('tc_id_error', hk.tc_id_error),
                ('tc_length_error', hk.tc_length_error),
                ('tc_crc_error', hk.tc_crc_error),
                (
                    'last_tc_status_raw',
                    f'0x{hk.last_tc_status:08X}',
                ),
                ('frame_counter', hk.frame_counter),
                ('abort_counter', hk.abort_counter),
                (
                    'command_error_counter',
                    hk.command_error_counter,
                ),
                ('uptime_seconds', hk.uptime_seconds),
            ],
        )

        if hk.all_monitors_valid:
            monitor_level = DiagnosticStatus.OK
            monitor_text = 'All monitor values valid'
        elif hk.any_monitors_valid:
            monitor_level = DiagnosticStatus.WARN
            monitor_text = 'Some monitor values are not valid'
        else:
            monitor_level = DiagnosticStatus.WARN
            monitor_text = 'Monitor values not valid'

        monitors = make_status(
            'Camera/Monitors',
            monitor_level,
            monitor_text,
            [
                ('monitor_valid_raw', f'0x{hk.monitor_valid:08X}'),

                (
                    'detector_temperature_valid',
                    hk.detector_temperature_valid,
                ),
                ('detector_temperature_raw', hk.temp_detector),

                ('vdd20_voltage_valid', hk.vdd20_voltage_valid),
                ('vdd20_voltage_raw', hk.vdd20_voltage),

                (
                    'core_1v2_current_valid',
                    hk.core_1v2_current_valid,
                ),
                ('core_1v2_current_raw', hk.core_1v2_current),

                (
                    'core_1v2_voltage_valid',
                    hk.core_1v2_voltage_valid,
                ),
                ('core_1v2_voltage_raw', hk.core_1v2_voltage),

                (
                    'io_3v3_current_valid',
                    hk.io_3v3_current_valid,
                ),
                ('io_3v3_current_raw', hk.io_3v3_current),

                (
                    'io_3v3_voltage_valid',
                    hk.io_3v3_voltage_valid,
                ),
                ('io_3v3_voltage_raw', hk.io_3v3_voltage),

                (
                    'input_5v_current_valid',
                    hk.input_5v_current_valid,
                ),
                ('input_5v_current_raw', hk.input_5v_current),

                (
                    'fpga_temperature_valid',
                    hk.fpga_temperature_valid,
                ),
                ('fpga_temperature_raw', hk.temp_fpga),

                (
                    'power_temperature_valid',
                    hk.power_temperature_valid,
                ),
                ('power_temperature_raw', hk.temp_power),
            ],
        )

        camera_spw_error = (
            hk.spw_error_counter != 0
            or hk.last_spw_error != 0
        )

        camera_spw = make_status(
            'Camera/SpaceWire',
            (
                DiagnosticStatus.ERROR
                if camera_spw_error
                else DiagnosticStatus.OK
            ),
            (
                'Camera SpaceWire errors detected'
                if camera_spw_error
                else 'Camera SpaceWire diagnostics clear'
            ),
            [
                ('rx_packet_counter', hk.spw_rx_packet_counter),
                ('tx_packet_counter', hk.spw_tx_packet_counter),
                ('error_counter', hk.spw_error_counter),
                ('last_error', f'0x{hk.last_spw_error:08X}'),
            ],
        )

        msg.status = [
            identification,
            state,
            configuration,
            counters,
            monitors,
            camera_spw,
        ]

        self.housekeeping_pub.publish(msg)

        response.success = True
        response.message = (
            f'Camera housekeeping received; '
            f'TC={hk.tc_counter}, '
            f'frames={hk.frame_counter}'
        )

        self.get_logger().info(response.message)
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
