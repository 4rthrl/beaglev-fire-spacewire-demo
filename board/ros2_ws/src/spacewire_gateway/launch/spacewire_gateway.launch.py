from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='spacewire_gateway',
            executable='gateway',
            name='spacewire_gateway',
            output='screen',
            parameters=[
                {'hardware_backend': 'beaglev'},
            ],
            remappings=[
                ('/diagnostics', '/spacewire/diagnostics'),
                ('/camera/image', '/spacewire/camera/image'),
                ('/spacewire/connect', '/spacewire/link/connect'),
                ('/spacewire/disconnect', '/spacewire/link/disconnect'),
                ('/camera/request_image', '/spacewire/camera/request_image'),
                (
                    '/camera/get_housekeeping',
                    '/spacewire/camera/get_housekeeping',
                ),
                (
                    '/camera/housekeeping',
                    '/spacewire/camera/housekeeping',
                ),
            ],
        ),
    ])
