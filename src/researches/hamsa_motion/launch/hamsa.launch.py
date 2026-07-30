import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share = get_package_share_directory('hamsa_motion')
    config_file = os.path.join(pkg_share, 'config', 'hamsa_params.yaml')

    return LaunchDescription([
        Node(
            package='hamsa_motion',
            executable='hamsa_motion_node',
            name='hamsa_motion_node',
            output='screen',
            parameters=[config_file]
        )
    ])
