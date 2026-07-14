# ROS2 ORB-SLAM2 RGB-D 点云建图复现工程

本工程是对原 `grsyz` 项目中 **ORB-SLAM2 RGB-D 点云建图系统** 的 ROS2 迁移版本，目标平台为：

```text
Jetson Orin Nano Super 8GB
Ubuntu 22.04
ROS2 Humble
Orbbec Femto Mega
```

工程使用 `pyorbbecsdk` 直接读取 Femto Mega 相机数据，并发布已经完成 **深度图对齐到彩色图** 的 RGB-D 话题，再由 ROS2 版 ORB-SLAM2 节点完成相机跟踪、关键帧建图和点云保存。

---

## 1. 功能概览

本迁移版支持：

- 启动 Femto Mega 对齐 RGB-D 发布器；
- 发布 `/orbbec/aligned/color/image_raw` 和 `/orbbec/aligned/depth/image_raw`；
- 使用 ORB-SLAM2 RGB-D 模式进行室内场景跟踪；
- 保存相机轨迹和关键帧轨迹；
- 保存点云地图 `result.pcd`；
- 使用 `pcl_viewer`、CloudCompare 或 MeshLab 查看建图结果。

整体流程：

```text
Femto Mega
  -> pyorbbecsdk depth-to-color alignment
  -> ROS2 aligned RGB-D topics
  -> ORB-SLAM2 RGB-D tracking
  -> keyframe point cloud fusion
  -> result.pcd
```

---

## 2. 目录结构

```text
ros2_orbslam2_pointcloud_map/
├── README.md
├── scripts/
│   ├── build_orbslam2_core.sh
│   └── build_ros2_ws.sh
├── src/
│   └── orbslam2_pointcloud_ros2/
│       ├── CMakeLists.txt
│       ├── package.xml
│       ├── config/
│       │   ├── femto_mega.yaml
│       │   └── femto_mega_aligned.yaml
│       ├── launch/
│       │   ├── orbbec_aligned_rgbd_publisher.launch.py
│       │   ├── rgbd_femto_mega.launch.py
│       │   └── femto_mega_camera_and_slam.launch.py
│       ├── scripts/
│       │   └── orbbec_aligned_rgbd_publisher.py
│       └── src/
│           └── rgbd_node.cpp
└── docs/
    ├── ORBBEC_ALIGNED_RGBD_PUBLISHER.md
    ├── MIGRATION_NOTES.md
    └── JETSON_ORIN_NANO_UBUNTU22_ROS2_REPRODUCE.md
```

原 ORB-SLAM2 点云核心库应位于同级 `main` 目录下：

```text
../main/ORBSLAM2_with_pointcloudmap_AstraPro-main/ORBSLAM2_with_pointcloud_map
```

在 Jetson 上的推荐完整路径为：

```text
/home/jetson/ws/orb-slam2/code/main/ORBSLAM2_with_pointcloudmap_AstraPro-main/ORBSLAM2_with_pointcloud_map
/home/jetson/ws/orb-slam2/code/ros2_orbslam2_pointcloud_map
```

---

## 3. 环境要求

### 3.1 硬件

| 名称 | 要求 |
| --- | --- |
| 开发板 | Jetson Orin Nano Super 8GB |
| 相机 | Orbbec Femto Mega |
| 运行方式 | 手持相机扫描室内场景 |

### 3.2 软件

| 名称 | 推荐版本 |
| --- | --- |
| Ubuntu | 22.04 |
| ROS2 | Humble |
| Python | 3.10 |
| pyorbbecsdk | `pyorbbecsdk2` |
| OpenCV | 建议 ORB-SLAM2 核心和 ROS2 节点使用同一套 OpenCV |
| PCL | `libpcl-dev` + `pcl-tools` |

安装常用依赖：

```bash
sudo apt update

sudo apt install -y \
  build-essential cmake git wget unzip \
  ros-humble-rclcpp \
  ros-humble-rclpy \
  ros-humble-sensor-msgs \
  ros-humble-std-msgs \
  ros-humble-message-filters \
  python3-colcon-common-extensions \
  python3-pip \
  libpcl-dev \
  pcl-tools
```

安装 Orbbec Python SDK：

```bash
pip3 install --upgrade pyorbbecsdk2
```

验证：

```bash
python3 -c "from pyorbbecsdk import Pipeline; print('pyorbbecsdk OK')"
```

完整复现教程也可参考：

```text
../../Jetson_Orin_Nano_ROS2_ORBSLAM2_房间三维重建复现教程.md
```
