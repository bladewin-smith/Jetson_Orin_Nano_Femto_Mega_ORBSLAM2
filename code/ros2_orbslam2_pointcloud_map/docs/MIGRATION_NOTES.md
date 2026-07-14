# ROS1 到 ROS2 迁移说明

本目录迁移的是原项目的 ROS 接入层，而不是重写 ORB-SLAM2 本体。原项目中负责位姿估计、关键帧管理、回环检测、点云融合与 `result.pcd` 保存的代码仍然由 `ORB_SLAM2_with_pointcloud_map` 提供。

## 功能映射

| ROS1 原功能 | ROS2 迁移后实现 |
|---|---|
| `ros::init` / `ros::NodeHandle` | `rclcpp::init` / `rclcpp::Node` |
| `message_filters::Subscriber<sensor_msgs::Image>` | `message_filters::Subscriber<sensor_msgs::msg::Image>` |
| ApproximateTime 同步 RGB 与 Depth | 保留 ApproximateTime 同步策略 |
| `cv_bridge::toCvShare` 转 `cv::Mat` | 保留 `cv_bridge::toCvShare` |
| `SLAM.TrackRGBD(rgb, depth, time)` | 保留同一调用 |
| `/RGBD/cmd` 收到 `stop` 后退出 | ROS2 下继续订阅 `/RGBD/cmd`，收到 `stop` 后保存轨迹并退出 |
| `CameraTrajectory.txt`、`KeyFrameTrajectory.txt` | 保存到 `output_dir` |
| `result.pcd` | 由原 `pointcloudmapping.cc` 在 SLAM shutdown 时保存 |

## 迁移边界

- `src/rgbd_node.cpp` 是新的 ROS2 节点入口。
- `config/femto_mega.yaml` 是面向 Orbbec Femto Mega 的参数模板。
- `launch/rgbd_femto_mega.launch.py` 默认只启动 SLAM 节点，相机驱动建议单独启动，便于调试话题。
- `launch/femto_mega_camera_and_slam.launch.py` 提供相机和 SLAM 同时启动的示例，但不同版本的 Orbbec 驱动参数名可能略有差异，必要时请以实际驱动为准。

## 需要人工校准的参数

`femto_mega.yaml` 中的相机内参只是占位值。复现时必须从 `/camera/color/camera_info` 中读取 `k` 矩阵并替换：

```yaml
Camera.fx: k[0]
Camera.fy: k[4]
Camera.cx: k[2]
Camera.cy: k[5]
```

同时确认深度图编码：

```bash
ros2 topic echo /camera/depth/image_raw --once
```

- 如果编码是 `16UC1`，通常深度单位是毫米，`DepthMapFactor` 设为 `1000.0`。
- 如果编码是 `32FC1`，通常深度单位是米，`DepthMapFactor` 设为 `1.0`。
