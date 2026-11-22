import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('project_alpha_ros')
    default_params_file = os.path.join(pkg_dir, 'config', 'alpha_params.yaml')

    params_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_params_file,
        description='Path to ROS 2 parameters YAML file'
    )

    motion_node = Node(
        package='project_alpha_ros',
        executable='alpha_motion_node',
        name='alpha_motion_node',
        output='screen',
        parameters=[LaunchConfiguration('params_file')]
    )

    brain_node = Node(
        package='project_alpha_ros',
        executable='alpha_brain_node',
        name='alpha_brain_node',
        output='screen',
        parameters=[LaunchConfiguration('params_file')]
    )

    face_voice_node = Node(
        package='project_alpha_ros',
        executable='alpha_face_voice_node',
        name='alpha_face_voice_node',
        output='screen',
        parameters=[LaunchConfiguration('params_file')]
    )

    return LaunchDescription([
        params_arg,
        motion_node,
        brain_node,
        face_voice_node,
    ])
