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

    prompt_file_arg = DeclareLaunchArgument(
        "prompt_file",
        default_value=os.path.join(get_package_share_directory('groq_ros'), 'config', 'groq_room.yaml'),
        description="Prompt data format file path",
    )

    function_list_arg = DeclareLaunchArgument(
        "function_list",
        default_value=os.path.join(get_package_share_directory('groq_ros'), 'config', 'groq_function_list.yaml'),
        description="Tool definition file path",
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
                "prompt_file": LaunchConfiguration("prompt_file"),
                "function_list_file": LaunchConfiguration("function_list"),
            },
            config_file_path
        ],
    )

    return LaunchDescription(
        [
            robot_name_arg,
            api_key_arg,
            prompt_file_arg,
            function_list_arg,
            groq_action_server_node,
        ]
    )
