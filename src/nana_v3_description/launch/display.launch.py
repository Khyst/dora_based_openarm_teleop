# Copyright 2025 Enactic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription, LaunchContext
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def robot_state_publisher_spawner(context: LaunchContext, model_path_sub):
    model_path = context.perform_substitution(model_path_sub)

    if not os.path.exists(model_path):
        pkg_share = get_package_share_directory("nana_v3_description")
        fallback_path = os.path.join(
            pkg_share, "assets", "robot", "urdf", os.path.basename(model_path)
        )
        if os.path.exists(fallback_path):
            model_path = fallback_path
        else:
            raise FileNotFoundError(f"URDF file not found at {model_path}")

    with open(model_path, "r", encoding="utf-8") as f:
        robot_description = f.read()

    return [
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            output="screen",
            parameters=[{"robot_description": robot_description}],
        )
    ]


def generate_launch_description():
    pkg_share = get_package_share_directory("nana_v3_description")

    default_model_path = os.path.join(
        pkg_share,
        "urdf",
        "nana_v4_corrected.urdf",
    )

    default_rviz_config_path = os.path.join(
        pkg_share,
        "rviz",
        "nana_v3_display.rviz",
    )

    model_arg = DeclareLaunchArgument(
        "model",
        default_value=default_model_path,
        description="Absolute path to preprocessed robot URDF file",
    )

    rviz_config_arg = DeclareLaunchArgument(
        "rviz_config",
        default_value=default_rviz_config_path,
        description="Absolute path to rviz config file",
    )

    model = LaunchConfiguration("model")
    rviz_config = LaunchConfiguration("rviz_config")

    return LaunchDescription([
        model_arg,
        rviz_config_arg,
        OpaqueFunction(
            function=robot_state_publisher_spawner,
            args=[model],
        ),
        Node(
            package="joint_state_publisher_gui",
            executable="joint_state_publisher_gui",
            name="joint_state_publisher_gui",
            output="screen",
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            output="screen",
            arguments=["-d", rviz_config],
        ),
    ])