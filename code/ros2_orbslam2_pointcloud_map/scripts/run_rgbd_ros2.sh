#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${ORB_SLAM2_ROOT:-}" ]]; then
  ORB_SLAM2_ROOT="$(cd "${WORKSPACE_DIR}/../main/ORBSLAM2_with_pointcloudmap_AstraPro-main/ORBSLAM2_with_pointcloud_map" && pwd)"
  export ORB_SLAM2_ROOT
fi

RESULT_DIR="${HOME}/orbslam2_pointcloud_results"
mkdir -p "${RESULT_DIR}"

source /opt/ros/humble/setup.bash
source "${WORKSPACE_DIR}/install/setup.bash"

cd "${RESULT_DIR}"

ros2 launch orbslam2_pointcloud_ros2 rgbd_femto_mega.launch.py \
  vocabulary_path:="${ORB_SLAM2_ROOT}/Vocabulary/ORBvoc.bin" \
  output_dir:="${RESULT_DIR}"
