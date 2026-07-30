import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    
    # 1. Declare launch arguments
    type_arg = DeclareLaunchArgument(
        'type',
        default_value='default',
        description="Type of the motion server to run (e.g. 'default' or 'joint_sync')"
    )

    pkg_share = get_package_share_directory('openarm_motion')
    default_json = os.path.join(pkg_share, 'json', 'motion', 'demo_06_18.json')
    
    file_arg = DeclareLaunchArgument(
        'file',
        default_value=default_json,
        description="Path to the JSON motion sequence file"
    )

    # 2. Load standard MoveIt configurations
    moveit_config = MoveItConfigsBuilder("nana_v3", package_name="nana_v3_moveit_config").to_moveit_configs()

    # 3. Convert to parameter dictionary
    moveit_params = moveit_config.to_dict()

    # 4. Get YAML config file path
    config_file_path = os.path.join(pkg_share, 'config', 'motion_params.yaml')

    # 5. Merge JSON parameters from launch argument and package layout
    moveit_params['json_file_path'] = LaunchConfiguration('file')
    moveit_params['json_dir'] = os.path.join(pkg_share, 'json', 'motion')

    # Determine executable dynamically based on 'type' argument
    executable_name = PythonExpression([
        "'motion_action_server_joint_states_sync' if '",
        LaunchConfiguration('type'),
        "' == 'joint_sync' else 'motion_action_server'"
    ])

    # 6. Launch node with combined parameters
    return LaunchDescription([
        type_arg,
        file_arg,
        Node(
            package='openarm_motion',
            executable=executable_name,
            name='motion_action_server',
            output='screen',
            parameters=[moveit_params, config_file_path]
        )
    ])
