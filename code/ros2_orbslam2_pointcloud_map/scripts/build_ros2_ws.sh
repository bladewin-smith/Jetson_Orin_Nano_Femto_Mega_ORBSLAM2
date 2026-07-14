#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${ORB_SLAM2_ROOT:-}" ]]; then
  ORB_SLAM2_ROOT="$(cd "${WORKSPACE_DIR}/../main/ORBSLAM2_with_pointcloudmap_AstraPro-main/ORBSLAM2_with_pointcloud_map" && pwd)"
  export ORB_SLAM2_ROOT
fi
set +u
source /opt/ros/humble/setup.bash
set -u
cd "${WORKSPACE_DIR}"
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

echo
echo "ROS 2 workspace build finished:"
echo "source ${WORKSPACE_DIR}/install/setup.bash"
