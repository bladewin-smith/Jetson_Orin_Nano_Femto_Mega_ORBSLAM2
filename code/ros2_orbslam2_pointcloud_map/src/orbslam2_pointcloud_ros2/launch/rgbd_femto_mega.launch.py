import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package_share = FindPackageShare("orbslam2_pointcloud_ros2")
    default_settings = PathJoinSubstitution([package_share, "config", "femto_mega.yaml"])
    default_vocabulary = PathJoinSubstitution([
        EnvironmentVariable("ORB_SLAM2_ROOT", default_value="/opt/orbslam2_pointcloud_map"),
        "Vocabulary",
        "ORBvoc.bin",
    ])
    default_output_dir = os.path.expanduser("~/orbslam2_pointcloud_results")

    return LaunchDescription([
        DeclareLaunchArgument("vocabulary_path", default_value=default_vocabulary),
        DeclareLaunchArgument("settings_path", default_value=default_settings),
        DeclareLaunchArgument("rgb_topic", default_value=""),
        DeclareLaunchArgument("depth_topic", default_value=""),
        DeclareLaunchArgument("output_dir", default_value=default_output_dir),
        DeclareLaunchArgument("enable_viewer", default_value="true"),
        DeclareLaunchArgument("queue_size", default_value="10"),
        DeclareLaunchArgument("sync_slop_seconds", default_value="0.15"),
        Node(
            package="orbslam2_pointcloud_ros2",
            executable="rgbd_node",
            name="orbslam2_rgbd",
            output="screen",
            parameters=[{
                "vocabulary_path": LaunchConfiguration("vocabulary_path"),
                "settings_path": LaunchConfiguration("settings_path"),
                "rgb_topic": LaunchConfiguration("rgb_topic"),
                "depth_topic": LaunchConfiguration("depth_topic"),
                "output_dir": LaunchConfiguration("output_dir"),
                "enable_viewer": ParameterValue(LaunchConfiguration("enable_viewer"), value_type=bool),
                "queue_size": ParameterValue(LaunchConfiguration("queue_size"), value_type=int),
                "sync_slop_seconds": ParameterValue(LaunchConfiguration("sync_slop_seconds"), value_type=float),
            }],
        ),
    ])
