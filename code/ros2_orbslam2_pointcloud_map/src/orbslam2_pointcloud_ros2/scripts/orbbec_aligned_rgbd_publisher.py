#!/usr/bin/env python3
"""Publish Femto Mega RGB images and depth images aligned to the RGB camera.

This node talks to the camera through pyorbbecsdk directly. Stop the official
orbbec_camera node before launching it, otherwise the device may be occupied.
"""

import sys
import time
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CameraInfo, Image

from pyorbbecsdk import (
    AlignFilter,
    Config,
    OBAlignMode,
    OBFormat,
    OBFrameAggregateOutputMode,
    OBSensorType,
    OBStreamType,
    Pipeline,
)


class OrbbecAlignedRgbdPublisher(Node):
    def __init__(self) -> None:
        super().__init__("orbbec_aligned_rgbd_publisher")

        self.declare_parameter("color_topic", "/orbbec/aligned/color/image_raw")
        self.declare_parameter("depth_topic", "/orbbec/aligned/depth/image_raw")
        self.declare_parameter("color_info_topic", "/orbbec/aligned/color/camera_info")
        self.declare_parameter("depth_info_topic", "/orbbec/aligned/depth/camera_info")
        self.declare_parameter("frame_id", "orbbec_color_optical_frame")
        self.declare_parameter("fps", 30)
        self.declare_parameter("use_hw_d2c", False)
        self.declare_parameter("enable_frame_sync", True)
        self.declare_parameter("publish_rate_hz", 0.0)

        self.color_topic = self.get_parameter("color_topic").value
        self.depth_topic = self.get_parameter("depth_topic").value
        self.color_info_topic = self.get_parameter("color_info_topic").value
        self.depth_info_topic = self.get_parameter("depth_info_topic").value
        self.frame_id = self.get_parameter("frame_id").value
        self.fps = int(self.get_parameter("fps").value)
        self.use_hw_d2c = bool(self.get_parameter("use_hw_d2c").value)
        self.enable_frame_sync = bool(self.get_parameter("enable_frame_sync").value)
        self.publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)

        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
            reliability=ReliabilityPolicy.BEST_EFFORT,
        )
        info_qos = QoSProfile(depth=5)

        self.color_pub = self.create_publisher(Image, self.color_topic, qos)
        self.depth_pub = self.create_publisher(Image, self.depth_topic, qos)
        self.color_info_pub = self.create_publisher(CameraInfo, self.color_info_topic, info_qos)
        self.depth_info_pub = self.create_publisher(CameraInfo, self.depth_info_topic, info_qos)

        self.pipeline = Pipeline()
        self.config = Config()
        self.align_filter: Optional[AlignFilter] = None
        self.camera_info: Optional[CameraInfo] = None
        self.depth_scale = 1.0

    def start_camera(self) -> None:
        color_profiles = self.pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
        try:
            color_profile = color_profiles.get_video_stream_profile(0, 0, OBFormat.RGB, self.fps)
        except Exception:
            color_profile = color_profiles.get_video_stream_profile(0, 0, OBFormat.RGB, 0)
        self.config.enable_stream(color_profile)

        if self.use_hw_d2c:
            depth_profiles = self.pipeline.get_d2c_depth_profile_list(color_profile, OBAlignMode.HW_MODE)
            if len(depth_profiles) == 0:
                raise RuntimeError("Femto Mega did not return a hardware D2C depth profile.")
            self.config.enable_stream(depth_profiles[0])
            self.config.set_align_mode(OBAlignMode.HW_MODE)
            self.get_logger().info("Using Orbbec hardware D2C alignment.")
        else:
            depth_profiles = self.pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
            self.config.enable_stream(depth_profiles.get_default_video_stream_profile())
            self.config.set_frame_aggregate_output_mode(OBFrameAggregateOutputMode.FULL_FRAME_REQUIRE)
            self.align_filter = AlignFilter(align_to_stream=OBStreamType.COLOR_STREAM)
            self.get_logger().info("Using pyorbbecsdk software depth-to-color alignment.")

        if self.enable_frame_sync:
            try:
                self.pipeline.enable_frame_sync()
                self.get_logger().info("Frame sync enabled.")
            except Exception as exc:  # pyorbbecsdk may reject sync on some firmware.
                self.get_logger().warn(f"Frame sync could not be enabled: {exc}")

        self.pipeline.start(self.config)
        self._wait_for_camera_param()

    def _wait_for_camera_param(self) -> None:
        for _ in range(30):
            frames = self.pipeline.wait_for_frames(1000)
            if frames is None:
                continue
            if self.align_filter is not None:
                frames = self.align_filter.process(frames)
            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()
            if color_frame is None or depth_frame is None:
                continue

            self.depth_scale = float(depth_frame.get_depth_scale())
            width = color_frame.get_width()
            height = color_frame.get_height()
            self.camera_info = self._make_camera_info(width, height)
            self.get_logger().info(
                f"Aligned stream ready: color/depth {width}x{height}, "
                f"depth_scale={self.depth_scale:.6f}"
            )
            return
        raise RuntimeError("Could not receive synchronized color and depth frames from the camera.")

    def _make_camera_info(self, width: int, height: int) -> CameraInfo:
        cam_param = self.pipeline.get_camera_param()
        intr = cam_param.rgb_intrinsic
        dist = cam_param.rgb_distortion

        msg = CameraInfo()
        msg.header.frame_id = self.frame_id
        msg.width = width
        msg.height = height
        msg.distortion_model = "plumb_bob"
        msg.d = [
            float(dist.k1),
            float(dist.k2),
            float(dist.p1),
            float(dist.p2),
            float(dist.k3),
        ]
        msg.k = [
            float(intr.fx), 0.0, float(intr.cx),
            0.0, float(intr.fy), float(intr.cy),
            0.0, 0.0, 1.0,
        ]
        msg.r = [
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0,
        ]
        msg.p = [
            float(intr.fx), 0.0, float(intr.cx), 0.0,
            0.0, float(intr.fy), float(intr.cy), 0.0,
            0.0, 0.0, 1.0, 0.0,
        ]
        self.get_logger().info(
            "RGB intrinsics for aligned depth: "
            f"fx={float(intr.fx):.3f} fy={float(intr.fy):.3f} "
            f"cx={float(intr.cx):.3f} cy={float(intr.cy):.3f}"
        )
        return msg

    def spin_camera(self) -> None:
        min_period = 0.0 if self.publish_rate_hz <= 0.0 else 1.0 / self.publish_rate_hz
        last_publish = 0.0

        while rclpy.ok():
            frames = self.pipeline.wait_for_frames(1000)
            if frames is None:
                rclpy.spin_once(self, timeout_sec=0.0)
                continue

            if self.align_filter is not None:
                frames = self.align_filter.process(frames)

            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()
            if color_frame is None or depth_frame is None:
                continue

            now = time.monotonic()
            if min_period > 0.0 and now - last_publish < min_period:
                continue
            last_publish = now

            try:
                color_image = self._color_frame_to_rgb(color_frame)
                depth_image = self._depth_frame_to_uint16(depth_frame)
            except ValueError as exc:
                self.get_logger().warn(str(exc))
                continue

            if color_image.shape[:2] != depth_image.shape[:2]:
                self.get_logger().warn(
                    f"Aligned frame size mismatch: color={color_image.shape} "
                    f"depth={depth_image.shape}"
                )
                continue

            stamp = self.get_clock().now().to_msg()
            color_msg = self._make_image_msg(color_image, "rgb8", stamp)
            depth_msg = self._make_image_msg(depth_image, "16UC1", stamp)
            info_msg = CameraInfo()
            info_msg = self.camera_info if self.camera_info is not None else info_msg
            info_msg.header.stamp = stamp

            self.color_pub.publish(color_msg)
            self.depth_pub.publish(depth_msg)
            self.color_info_pub.publish(info_msg)
            self.depth_info_pub.publish(info_msg)
            rclpy.spin_once(self, timeout_sec=0.0)

    def stop_camera(self) -> None:
        self.pipeline.stop()

    def _color_frame_to_rgb(self, frame) -> np.ndarray:
        if frame.get_format() != OBFormat.RGB:
            raise ValueError(f"Expected RGB color frame, got Orbbec format {frame.get_format()}.")
        height = frame.get_height()
        width = frame.get_width()
        data = np.frombuffer(frame.get_data(), dtype=np.uint8)
        expected = width * height * 3
        if data.size != expected:
            raise ValueError(f"Unexpected RGB frame size: got {data.size}, expected {expected}.")
        return np.ascontiguousarray(data.reshape((height, width, 3)))

    def _depth_frame_to_uint16(self, frame) -> np.ndarray:
        height = frame.get_height()
        width = frame.get_width()
        data = np.frombuffer(frame.get_data(), dtype=np.uint16)
        expected = width * height
        if data.size != expected:
            raise ValueError(f"Unexpected depth frame size: got {data.size}, expected {expected}.")
        return np.ascontiguousarray(data.reshape((height, width)))

    def _make_image_msg(self, image: np.ndarray, encoding: str, stamp) -> Image:
        msg = Image()
        msg.header.stamp = stamp
        msg.header.frame_id = self.frame_id
        msg.height = int(image.shape[0])
        msg.width = int(image.shape[1])
        msg.encoding = encoding
        msg.is_bigendian = False
        msg.step = int(image.strides[0])
        msg.data = image.tobytes()
        return msg


def main() -> int:
    rclpy.init()
    node = OrbbecAlignedRgbdPublisher()
    try:
        node.start_camera()
        node.spin_camera()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        node.get_logger().error(str(exc))
        return 1
    finally:
        try:
            node.stop_camera()
        except Exception:
            pass
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
