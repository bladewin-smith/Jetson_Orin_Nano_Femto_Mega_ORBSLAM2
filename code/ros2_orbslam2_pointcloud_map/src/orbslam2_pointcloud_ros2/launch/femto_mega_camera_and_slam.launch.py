from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    orbbec_launch = PathJoinSubstitution([
        FindPackageShare("orbbec_camera"),
        "launch",
        "femto_mega.launch.py",
    ])
    package_share = FindPackageShare("orbslam2_pointcloud_ros2")
    settings_path = PathJoinSubstitution([package_share, "config", "femto_mega.yaml"])

    return LaunchDescription([
        DeclareLaunchArgument("launch_camera", default_value="true"),
        DeclareLaunchArgument("vocabulary_path"),
        DeclareLaunchArgument("output_dir", default_value="/tmp/orbslam2_pointcloud_results"),
        DeclareLaunchArgument("enable_viewer", default_value="true"),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(orbbec_launch),
            condition=IfCondition(LaunchConfiguration("launch_camera")),
            launch_arguments={
                "enable_align_depth": "true",
            }.items(),
        ),
        Node(
            package="orbslam2_pointcloud_ros2",
            executable="rgbd_node",
            name="orbslam2_rgbd",
            output="screen",
            parameters=[{
                "vocabulary_path": LaunchConfiguration("vocabulary_path"),
                "settings_path": settings_path,
                "output_dir": LaunchConfiguration("output_dir"),
                "enable_viewer": ParameterValue(LaunchConfiguration("enable_viewer"), value_type=bool),
            }],
        ),
    ])
