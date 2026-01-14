import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    robot_name_arg = DeclareLaunchArgument(
        "robot_name",
        default_value="",
        description="Name of the robot",
    )

    api_key_arg = DeclareLaunchArgument(
        "api_key",
        default_value=os.getenv("GROQ_API_KEY", ""),
        description="Groq API Key",
    )

    rooms_file_arg = DeclareLaunchArgument(
        "rooms_file",
        default_value=os.path.join(get_package_share_directory('groq_ros'), 'config', 'groq_room.yaml'),
        description="Prompt data format file path",
    )

    config_file_path = os.path.join(
        get_package_share_directory('groq_ros'), "config", "groq_config.yaml"
    )

    groq_action_server_node = Node(
        package="groq_ros",
        executable="groq_action_server",
        name="groq_action_server",
        namespace=LaunchConfiguration("robot_name"),
        output="screen",
        parameters=[
            {
                "api_key": LaunchConfiguration("api_key"),
                "rooms_file": LaunchConfiguration("rooms_file"),
            },
            config_file_path
        ],
    )

    return LaunchDescription(
        [
            robot_name_arg,
            api_key_arg,
            rooms_file_arg,
            groq_action_server_node,
        ]
    )