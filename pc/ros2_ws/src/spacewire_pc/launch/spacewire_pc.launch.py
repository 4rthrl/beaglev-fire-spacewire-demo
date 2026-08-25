from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    package_share = get_package_share_directory('spacewire_pc')
    diagnostics_config = f'{package_share}/config/diagnostics.yaml'

    gui_dir = LaunchConfiguration('gui_dir')

    ros_remappings = [
        '/diagnostics:=/spacewire/diagnostics',
        '/camera/image:=/spacewire/camera/image',
        '/spacewire/connect:=/spacewire/link/connect',
        '/spacewire/disconnect:=/spacewire/link/disconnect',
        '/camera/request_image:=/spacewire/camera/request_image',
        '/camera/get_housekeeping:=/spacewire/camera/get_housekeeping',
        '/camera/housekeeping:=/spacewire/camera/housekeeping',
    ]

    aggregator = Node(
        package='diagnostic_aggregator',
        executable='aggregator_node',
        name='spacewire_diagnostic_aggregator',
        output='screen',
        parameters=[diagnostics_config],
        remappings=[
            ('/diagnostics', '/spacewire/diagnostics'),
            ('/diagnostics_agg', '/spacewire/diagnostics_agg'),
            (
                '/diagnostics_toplevel_state',
                '/spacewire/diagnostics_toplevel_state',
            ),
        ],
    )

    gui = ExecuteProcess(
        cmd=[
            'python3',
            '-m',
            'spacewire_gui',
            '--backend',
            'ros',
            '--ros-args',
            *sum([['-r', remap] for remap in ros_remappings], []),
        ],
        cwd=gui_dir,
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'gui_dir',
            description='Path to the SpaceWire GUI directory',
        ),
        aggregator,
        gui,
    ])
