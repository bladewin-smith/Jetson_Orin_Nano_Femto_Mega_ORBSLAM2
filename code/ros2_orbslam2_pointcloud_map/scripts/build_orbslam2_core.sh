#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${ORB_SLAM2_ROOT:-}" ]]; then
  ORB_SLAM2_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../main/ORBSLAM2_with_pointcloudmap_AstraPro-main/ORBSLAM2_with_pointcloud_map" && pwd)"
fi

echo "Building ORB-SLAM2 point cloud core at: ${ORB_SLAM2_ROOT}"
cd "${ORB_SLAM2_ROOT}"
chmod +x build.sh

# 定义日志文件路径
LOG_FILE="${ORB_SLAM2_ROOT}/build_$(date +%Y%m%d_%H%M%S).log"

# 执行编译并保存所有输出到日志，同时在终端显示
./build.sh 2>&1 | tee "${LOG_FILE}"

echo
echo "Core build finished. Build log saved to: ${LOG_FILE}"
echo "Keep this in your shell before building ROS 2:"
echo "export ORB_SLAM2_ROOT=${ORB_SLAM2_ROOT}"
