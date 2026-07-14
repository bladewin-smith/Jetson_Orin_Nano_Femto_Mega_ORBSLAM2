# 基于 ROS2 的 ORB-SLAM2 室内三维重建复现工程

本文件夹是对原 `grsyz` 项目的 ROS2 迁移版本，目标平台为 Jetson Orin Nano Super 8GB + Ubuntu 22.04 + ROS2 Humble + Orbbec Femto Mega。

## 目录结构

```text
ros2_orbslam2_pointcloud_map/
├── src/orbslam2_pointcloud_ros2/
│   ├── src/rgbd_node.cpp
│   ├── config/femto_mega.yaml
│   ├── launch/rgbd_femto_mega.launch.py
│   ├── launch/femto_mega_camera_and_slam.launch.py
│   ├── CMakeLists.txt
│   └── package.xml
├── scripts/
│   ├── build_orbslam2_core.sh
│   ├── build_ros2_ws.sh
│   └── run_rgbd_ros2.sh
└── docs/MIGRATION_NOTES.md
```

## 复现流程概览

1. 安装 ROS2 Humble、Orbbec Femto Mega ROS2 驱动和 C++/PCL/OpenCV 依赖。
2. 编译原 ORB-SLAM2 点云核心库。
3. 修改 `femto_mega.yaml` 中的相机内参、深度比例和话题名。
4. 编译本 ROS2 工作区。
5. 启动 Femto Mega 相机，确认 RGB 与 Depth 话题正常。
6. 启动 `orbslam2_pointcloud_ros2` 节点。
7. 扫描室内场景，发送 `stop` 指令保存点云和轨迹。

## 快速命令

```bash
cd ~/grsyz/ros2_orbslam2_pointcloud_map
chmod +x scripts/*.sh

./scripts/build_orbslam2_core.sh
./scripts/build_ros2_ws.sh
```

启动相机：

```bash
source /opt/ros/humble/setup.bash
ros2 launch orbbec_camera femto_mega.launch.py enable_align_depth:=true
```

另开终端启动 SLAM：

```bash
cd ~/grsyz/ros2_orbslam2_pointcloud_map
./scripts/run_rgbd_ros2.sh
```

停止并保存：

```bash
ros2 topic pub --once /RGBD/cmd std_msgs/msg/String "{data: stop}"
```

输出文件默认位于：

```text
~/orbslam2_pointcloud_results/result.pcd
~/orbslam2_pointcloud_results/CameraTrajectory.txt
~/orbslam2_pointcloud_results/KeyFrameTrajectory.txt
```
