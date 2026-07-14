cmake_minimum_required(VERSION 3.8)
project(orbslam2_pointcloud_ros2)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_compile_options(-O3 -Wall -Wextra)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(message_filters REQUIRED)
find_package(OpenCV REQUIRED)
find_package(Eigen3 REQUIRED)
find_package(Pangolin REQUIRED)
find_package(PCL REQUIRED)

if(DEFINED ENV{ORB_SLAM2_ROOT})
  set(ORB_SLAM2_ROOT "$ENV{ORB_SLAM2_ROOT}" CACHE PATH "Path to ORB_SLAM2_with_pointcloud_map")
else()
  set(ORB_SLAM2_ROOT
    "${CMAKE_CURRENT_LIST_DIR}/../../../main/ORBSLAM2_with_pointcloudmap_AstraPro-main/ORBSLAM2_with_pointcloud_map"
    CACHE PATH "Path to ORB_SLAM2_with_pointcloud_map")
endif()

if(NOT EXISTS "${ORB_SLAM2_ROOT}/include/System.h")
  message(FATAL_ERROR
    "ORB_SLAM2_ROOT is invalid. Set it to ORB_SLAM2_with_pointcloud_map, for example: "
    "export ORB_SLAM2_ROOT=/home/jetson/grsyz/main/ORBSLAM2_with_pointcloudmap_AstraPro-main/ORBSLAM2_with_pointcloud_map")
endif()

if(NOT EXISTS "${ORB_SLAM2_ROOT}/lib/libORB_SLAM2.so")
  message(FATAL_ERROR
    "libORB_SLAM2.so was not found. Build the original ORB-SLAM2 point cloud core before colcon build.")
endif()

include_directories(
  ${ORB_SLAM2_ROOT}
  ${ORB_SLAM2_ROOT}/include
  ${EIGEN3_INCLUDE_DIRS}
  ${Pangolin_INCLUDE_DIRS}
  ${PCL_INCLUDE_DIRS}
)

add_definitions(${PCL_DEFINITIONS})
link_directories(${PCL_LIBRARY_DIRS})

add_executable(rgbd_node src/rgbd_node.cpp)

ament_target_dependencies(rgbd_node
  rclcpp
  sensor_msgs
  std_msgs
  message_filters
)

target_link_libraries(rgbd_node
  ${ORB_SLAM2_ROOT}/lib/libORB_SLAM2.so
  ${ORB_SLAM2_ROOT}/Thirdparty/DBoW2/lib/libDBoW2.so
  ${ORB_SLAM2_ROOT}/Thirdparty/g2o/lib/libg2o.so
  ${OpenCV_LIBS}
  ${Pangolin_LIBRARIES}
  ${PCL_LIBRARIES}
)

set_target_properties(rgbd_node PROPERTIES
  BUILD_RPATH "${ORB_SLAM2_ROOT}/lib;${ORB_SLAM2_ROOT}/Thirdparty/DBoW2/lib;${ORB_SLAM2_ROOT}/Thirdparty/g2o/lib"
  INSTALL_RPATH "${ORB_SLAM2_ROOT}/lib;${ORB_SLAM2_ROOT}/Thirdparty/DBoW2/lib;${ORB_SLAM2_ROOT}/Thirdparty/g2o/lib"
)

install(TARGETS rgbd_node
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/orbbec_aligned_rgbd_publisher.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
