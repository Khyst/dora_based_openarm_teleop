import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Find package share directory
    pkg_share = FindPackageShare(package='nana_v4_description').find('nana_v4_description')

    # Path to default xacro file
    default_model_path = os.path.join(
        pkg_share,
        'models',
        'nana_v4',
        'urdf',
        'robot',
        'nana_v4.urdf.xacro'
    )

    # Path to rviz config file
    rviz_config_path = os.path.join(pkg_share, 'rviz', 'nana_v4_display.rviz')

    # Declare launch arguments
    model_arg = DeclareLaunchArgument(
        name='model',
        default_value=default_model_path,
        description='Absolute path to robot xacro file'
    )

    rviz_config_arg = DeclareLaunchArgument(
        name='rvizconfig',
        default_value=rviz_config_path,
        description='Absolute path to rviz config file'
    )

    # Process xacro to generate URDF string
    robot_description_content = Command([
        'xacro ', LaunchConfiguration('model')
    ])

    robot_description = {'robot_description': robot_description_content}

    # Robot State Publisher Node
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[robot_description]
    )

    # Joint State Publisher GUI Node (for joint limits and GUI sliders)
    joint_state_publisher_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen'
    )

    # RViz2 Node
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', LaunchConfiguration('rvizconfig')]
    )

    return LaunchDescription([
        model_arg,
        rviz_config_arg,
        robot_state_publisher_node,
        joint_state_publisher_gui_node,
        rviz_node
    ])
