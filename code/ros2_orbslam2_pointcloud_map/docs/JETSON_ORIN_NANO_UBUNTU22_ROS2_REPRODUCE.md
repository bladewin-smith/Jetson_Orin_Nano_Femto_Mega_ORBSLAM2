# Jetson Orin Nano + Ubuntu 22.04 + ROS2 复现步骤

目标设备：

```text
Jetson Orin Nano Super 8GB
Ubuntu 22.04
ROS2 Humble
Orbbec Femto Mega
```

## 1. 准备系统依赖

```bash
sudo apt update
sudo apt install -y \
  build-essential cmake git pkg-config \
  libopencv-dev libeigen3-dev libpcl-dev libboost-all-dev \
  libglew-dev libgl1-mesa-dev libglu1-mesa-dev \
  ros-humble-cv-bridge ros-humble-message-filters \
  ros-humble-image-transport ros-humble-rviz2 \
  python3-colcon-common-extensions python3-rosdep
```

如果系统没有 Pangolin：

```bash
sudo apt install -y libpangolin-dev
```

若 `libpangolin-dev` 不可用，请从 Pangolin 源码编译安装。

Jetson 设备建议开启较大的 swap，避免编译 ORB-SLAM2 / PCL 时内存吃紧。

## 2. 安装 Femto Mega ROS2 驱动

优先使用 Orbbec 官方 ROS2 驱动。若 apt 源中没有现成包，可源码编译：

```bash
source /opt/ros/humble/setup.bash

mkdir -p ~/orbbec_ws/src
cd ~/orbbec_ws/src
git clone https://github.com/orbbec/OrbbecSDK_ROS2.git

cd ~/orbbec_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

安装 udev 规则后重新插拔相机。不同版本驱动脚本路径可能略有变化，若仓库内提供 `install_udev_rules.sh`，执行它即可。

启动相机：

```bash
source /opt/ros/humble/setup.bash
source ~/orbbec_ws/install/setup.bash
ros2 launch orbbec_camera femto_mega.launch.py enable_align_depth:=true
```

检查话题：

```bash
ros2 topic list
ros2 topic echo /camera/color/camera_info --once
ros2 topic echo /camera/depth/image_raw --once
```

记录 RGB、Depth、CameraInfo 的真实话题名。如果实际话题不是 `/camera/color/image_raw` 和 `/camera/depth/image_raw`，需要同步改配置。

## 3. 修改 Femto Mega 参数

打开：

```text
ros2_orbslam2_pointcloud_map/src/orbslam2_pointcloud_ros2/config/femto_mega.yaml
```

把 `/camera/color/camera_info` 中的 `k` 矩阵写入：

```yaml
Camera.fx: k[0]
Camera.fy: k[4]
Camera.cx: k[2]
Camera.cy: k[5]
```

确认深度图编码：

```text
16UC1 -> DepthMapFactor: 1000.0
32FC1 -> DepthMapFactor: 1.0
```

建议开启深度对齐到彩色图，否则 RGB 像素和深度像素无法一一对应，点云会出现明显错位。

## 4. 准备原 ORB-SLAM2 点云核心

把整个 `grsyz` 文件夹放到 Jetson，例如：

```text
~/grsyz
```

核心源码路径应为：

```text
~/grsyz/main/ORBSLAM2_with_pointcloudmap_AstraPro-main/ORBSLAM2_with_pointcloud_map
```

设置环境变量：

```bash
export ORB_SLAM2_ROOT=~/grsyz/main/ORBSLAM2_with_pointcloudmap_AstraPro-main/ORBSLAM2_with_pointcloud_map
```

编译核心库：

```bash
cd ~/grsyz/ros2_orbslam2_pointcloud_map
chmod +x scripts/*.sh
./scripts/build_orbslam2_core.sh
```

编译成功后应看到：

```text
$ORB_SLAM2_ROOT/lib/libORB_SLAM2.so
$ORB_SLAM2_ROOT/Thirdparty/DBoW2/lib/libDBoW2.so
$ORB_SLAM2_ROOT/Thirdparty/g2o/lib/libg2o.so
```

## 5. 编译 ROS2 迁移工程

```bash
source /opt/ros/humble/setup.bash
source ~/orbbec_ws/install/setup.bash

cd ~/grsyz/ros2_orbslam2_pointcloud_map
export ORB_SLAM2_ROOT=~/grsyz/main/ORBSLAM2_with_pointcloudmap_AstraPro-main/ORBSLAM2_with_pointcloud_map
./scripts/build_ros2_ws.sh
```

## 6. 运行复现

终端 1：启动 Femto Mega。

```bash
source /opt/ros/humble/setup.bash
source ~/orbbec_ws/install/setup.bash
ros2 launch orbbec_camera femto_mega.launch.py enable_align_depth:=true
```

终端 2：启动 ORB-SLAM2 RGB-D 三维重建。

```bash
cd ~/grsyz/ros2_orbslam2_pointcloud_map
export ORB_SLAM2_ROOT=~/grsyz/main/ORBSLAM2_with_pointcloudmap_AstraPro-main/ORBSLAM2_with_pointcloud_map
./scripts/run_rgbd_ros2.sh
```

也可以手动指定话题：

```bash
ros2 launch orbslam2_pointcloud_ros2 rgbd_femto_mega.launch.py \
  vocabulary_path:=$ORB_SLAM2_ROOT/Vocabulary/ORBvoc.bin \
  settings_path:=~/grsyz/ros2_orbslam2_pointcloud_map/src/orbslam2_pointcloud_ros2/config/femto_mega.yaml \
  rgb_topic:=/camera/color/image_raw \
  depth_topic:=/camera/depth/image_raw \
  output_dir:=~/orbslam2_pointcloud_results
```

## 7. 扫描与保存

手持或固定相机缓慢移动，优先选择有纹理、有棱角的室内区域。白墙、玻璃、强反光表面对 ORB 特征不友好。

结束时发送停止指令：

```bash
ros2 topic pub --once /RGBD/cmd std_msgs/msg/String "{data: stop}"
```

输出结果：

```text
~/orbslam2_pointcloud_results/result.pcd
~/orbslam2_pointcloud_results/CameraTrajectory.txt
~/orbslam2_pointcloud_results/KeyFrameTrajectory.txt
```

查看点云：

```bash
pcl_viewer ~/orbslam2_pointcloud_results/result.pcd
```

## 8. 常见问题

### 点云尺度不对

优先检查 `DepthMapFactor`。Femto Mega 深度图若是 `16UC1`，通常应设为 `1000.0`。

### 点云和彩色图错位

确认相机驱动已开启深度对齐到彩色图，例如：

```bash
ros2 launch orbbec_camera femto_mega.launch.py enable_align_depth:=true
```

### 节点收不到图像

检查配置文件和实际话题是否一致：

```bash
ros2 topic list
```

可在启动时用 `rgb_topic:=... depth_topic:=...` 覆盖配置。

### ORB-SLAM2 很快丢失跟踪

降低相机移动速度，选择纹理更丰富的区域，并确认 RGB 图像曝光正常。

### 编译找不到 ORB-SLAM2

确认环境变量：

```bash
echo $ORB_SLAM2_ROOT
ls $ORB_SLAM2_ROOT/include/System.h
ls $ORB_SLAM2_ROOT/lib/libORB_SLAM2.so
```
