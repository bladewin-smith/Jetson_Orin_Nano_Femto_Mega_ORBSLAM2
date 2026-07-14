from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("color_topic", default_value="/orbbec/aligned/color/image_raw"),
        DeclareLaunchArgument("depth_topic", default_value="/orbbec/aligned/depth/image_raw"),
        DeclareLaunchArgument("color_info_topic", default_value="/orbbec/aligned/color/camera_info"),
        DeclareLaunchArgument("depth_info_topic", default_value="/orbbec/aligned/depth/camera_info"),
        DeclareLaunchArgument("frame_id", default_value="orbbec_color_optical_frame"),
        DeclareLaunchArgument("fps", default_value="30"),
        DeclareLaunchArgument("use_hw_d2c", default_value="false"),
        DeclareLaunchArgument("enable_frame_sync", default_value="true"),
        DeclareLaunchArgument("publish_rate_hz", default_value="0.0"),
        Node(
            package="orbslam2_pointcloud_ros2",
            executable="orbbec_aligned_rgbd_publisher.py",
            name="orbbec_aligned_rgbd_publisher",
            output="screen",
            parameters=[{
                "color_topic": LaunchConfiguration("color_topic"),
                "depth_topic": LaunchConfiguration("depth_topic"),
                "color_info_topic": LaunchConfiguration("color_info_topic"),
                "depth_info_topic": LaunchConfiguration("depth_info_topic"),
                "frame_id": LaunchConfiguration("frame_id"),
                "fps": ParameterValue(LaunchConfiguration("fps"), value_type=int),
                "use_hw_d2c": ParameterValue(LaunchConfiguration("use_hw_d2c"), value_type=bool),
                "enable_frame_sync": ParameterValue(LaunchConfiguration("enable_frame_sync"), value_type=bool),
                "publish_rate_hz": ParameterValue(LaunchConfiguration("publish_rate_hz"), value_type=float),
            }],
        ),
    ])
