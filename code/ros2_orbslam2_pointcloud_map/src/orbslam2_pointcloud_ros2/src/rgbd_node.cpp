#include <atomic>
#include <cstdlib>
#include <filesystem>
#include <functional>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>

#include <message_filters/subscriber.h>
#include <message_filters/sync_policies/approximate_time.h>
#include <message_filters/synchronizer.h>
#include <opencv2/core/core.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <std_msgs/msg/string.hpp>

#include "System.h"

class RGBDNode : public rclcpp::Node {
public:
  using ImageMsg = sensor_msgs::msg::Image;
  using SyncPolicy = message_filters::sync_policies::ApproximateTime<ImageMsg, ImageMsg>;
  using Synchronizer = message_filters::Synchronizer<SyncPolicy>;

  RGBDNode() : Node("orbslam2_rgbd") {
    const std::string vocabulary_path = declare_parameter<std::string>("vocabulary_path", "");
    const std::string settings_path = declare_parameter<std::string>("settings_path", "");
    const bool enable_viewer = declare_parameter<bool>("enable_viewer", true);
    queue_size_ = declare_parameter<int>("queue_size", 10);
    sync_slop_seconds_ = declare_parameter<double>("sync_slop_seconds", 0.15);
    output_dir_ = declare_parameter<std::string>("output_dir", ".");

    if (vocabulary_path.empty()) {
      throw std::runtime_error("Parameter 'vocabulary_path' is required.");
    }
    if (settings_path.empty()) {
      throw std::runtime_error("Parameter 'settings_path' is required.");
    }

    cv::FileStorage settings(settings_path, cv::FileStorage::READ);
    if (!settings.isOpened()) {
      throw std::runtime_error("Failed to open settings file: " + settings_path);
    }

    std::string rgb_topic = declare_parameter<std::string>("rgb_topic", "");
    std::string depth_topic = declare_parameter<std::string>("depth_topic", "");
    if (rgb_topic.empty()) {
      rgb_topic = readString(settings, "rgb_topic", "/camera/color/image_raw");
    }
    if (depth_topic.empty()) {
      depth_topic = readString(settings, "depth_topic", "/camera/depth/image_raw");
    }

    normalizeOutputDir();

    RCLCPP_INFO(get_logger(), "Vocabulary: %s", vocabulary_path.c_str());
    RCLCPP_INFO(get_logger(), "Settings: %s", settings_path.c_str());
    RCLCPP_INFO(get_logger(), "RGB topic: %s", rgb_topic.c_str());
    RCLCPP_INFO(get_logger(), "Depth topic: %s", depth_topic.c_str());
    RCLCPP_INFO(get_logger(), "Approximate sync slop: %.3f s", sync_slop_seconds_);

    if (!enable_viewer) {
      setenv("ORB_SLAM2_DISABLE_PCL_VIEWER", "1", 0);
      RCLCPP_INFO(get_logger(), "ORB-SLAM2 viewer and PCL cloud viewer are disabled.");
    }

    slam_ = std::make_unique<ORB_SLAM2::System>(
      vocabulary_path, settings_path, ORB_SLAM2::System::RGBD, enable_viewer);

    rgb_sub_.subscribe(this, rgb_topic, rmw_qos_profile_sensor_data);
    depth_sub_.subscribe(this, depth_topic, rmw_qos_profile_sensor_data);

    SyncPolicy sync_policy(queue_size_);
    sync_policy.setMaxIntervalDuration(rclcpp::Duration::from_seconds(sync_slop_seconds_));
    sync_ = std::make_shared<Synchronizer>(sync_policy);
    sync_->connectInput(rgb_sub_, depth_sub_);
    sync_->registerCallback(std::bind(&RGBDNode::grabRGBD, this,
                                      std::placeholders::_1, std::placeholders::_2));

    cmd_sub_ = create_subscription<std_msgs::msg::String>(
      "/RGBD/cmd", 10,
      [this](const std_msgs::msg::String::SharedPtr msg) {
        RCLCPP_INFO(get_logger(), "Command received: %s", msg->data.c_str());
        if (msg->data == "stop") {
          shutdownSlam();
          rclcpp::shutdown();
        }
      });
  }

  ~RGBDNode() override {
    shutdownSlam();
  }

  void shutdownSlam() {
    std::lock_guard<std::mutex> lock(shutdown_mutex_);
    if (shutdown_started_.exchange(true) || !slam_) {
      return;
    }

    RCLCPP_INFO(get_logger(), "Stopping ORB-SLAM2 threads and saving results...");
    slam_->Shutdown();

    const auto processed_frames = frame_count_.load();
    if (processed_frames == 0) {
      RCLCPP_WARN(get_logger(),
                  "No RGB-D frames were processed; skip trajectory saving to avoid empty ORB-SLAM2 trajectory access.");
      slam_.release();
      return;
    }

    slam_->SaveTrajectoryTUM(output_dir_ + "CameraTrajectory.txt");
    slam_->SaveKeyFrameTrajectoryTUM(output_dir_ + "KeyFrameTrajectory.txt");
    RCLCPP_INFO(get_logger(),
                "Saved CameraTrajectory.txt and KeyFrameTrajectory.txt in: %s, processed frames: %zu",
                output_dir_.c_str(), processed_frames);
  }

private:
  static std::string readString(const cv::FileStorage &settings,
                                const std::string &key,
                                const std::string &fallback) {
    const cv::FileNode node = settings[key];
    if (node.empty()) {
      return fallback;
    }
    std::string value;
    node >> value;
    return value.empty() ? fallback : value;
  }

  void normalizeOutputDir() {
    if (output_dir_.empty()) {
      output_dir_ = ".";
    }

    std::filesystem::path output_path(output_dir_);
    if (output_path.is_relative()) {
      output_path = std::filesystem::absolute(output_path);
    }
    std::filesystem::create_directories(output_path);
    std::filesystem::current_path(output_path);

    output_dir_ = output_path.string();
    const char last = output_dir_.back();
    if (last != '/' && last != '\\') {
      output_dir_ += "/";
    }
  }

  void grabRGBD(const ImageMsg::ConstSharedPtr &rgb_msg,
                const ImageMsg::ConstSharedPtr &depth_msg) {
    if (shutdown_started_.load() || !slam_) {
      return;
    }

    cv::Mat rgb_image;
    cv::Mat depth_image;

    try {
      rgb_image = imageMsgToMat(*rgb_msg, true);
      depth_image = imageMsgToMat(*depth_msg, false);
    } catch (const std::exception &ex) {
      RCLCPP_ERROR(get_logger(), "Failed to convert ROS image messages: %s", ex.what());
      return;
    }

    if (rgb_image.empty() || depth_image.empty()) {
      RCLCPP_WARN(get_logger(), "Received an empty RGB or depth image; skip this pair.");
      return;
    }

    if (rgb_image.rows != depth_image.rows || rgb_image.cols != depth_image.cols) {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 3000,
        "RGB image size (%dx%d) and depth image size (%dx%d) differ. Use aligned depth-to-color topic or matching stream profiles.",
        rgb_image.cols, rgb_image.rows, depth_image.cols, depth_image.rows);
      return;
    }

    const double timestamp = rclcpp::Time(rgb_msg->header.stamp).seconds();
    try {
      slam_->TrackRGBD(rgb_image, depth_image, timestamp);
    } catch (const cv::Exception &ex) {
      RCLCPP_ERROR(get_logger(), "OpenCV exception in ORB-SLAM2 TrackRGBD: %s", ex.what());
      RCLCPP_ERROR(get_logger(), "RGB encoding=%s size=%dx%d step=%u, depth encoding=%s size=%dx%d step=%u",
                   rgb_msg->encoding.c_str(), rgb_image.cols, rgb_image.rows, rgb_msg->step,
                   depth_msg->encoding.c_str(), depth_image.cols, depth_image.rows, depth_msg->step);
      return;
    } catch (const std::exception &ex) {
      RCLCPP_ERROR(get_logger(), "Exception in ORB-SLAM2 TrackRGBD: %s", ex.what());
      return;
    }
    const auto processed_frames = ++frame_count_;
    if (processed_frames == 1 || processed_frames % 30 == 0) {
      RCLCPP_INFO(get_logger(), "Processed RGB-D frames: %zu", processed_frames);
    }
  }

  static cv::Mat imageMsgToMat(const ImageMsg &msg, const bool color_image) {
    if (msg.height == 0 || msg.width == 0) {
      throw std::runtime_error("Image message has zero width or height.");
    }

    int type = -1;
    size_t bytes_per_pixel = 0;
    if (color_image && (msg.encoding == "rgb8" || msg.encoding == "bgr8")) {
      type = CV_8UC3;
      bytes_per_pixel = 3;
    } else if (color_image && msg.encoding == "mono8") {
      type = CV_8UC1;
      bytes_per_pixel = 1;
    } else if (!color_image && msg.encoding == "16UC1") {
      type = CV_16UC1;
      bytes_per_pixel = 2;
    } else if (!color_image && msg.encoding == "32FC1") {
      type = CV_32FC1;
      bytes_per_pixel = 4;
    } else {
      throw std::runtime_error(
        std::string("Unsupported ") + (color_image ? "RGB" : "depth") +
        " image encoding: " + msg.encoding);
    }

    const size_t min_step = static_cast<size_t>(msg.width) * bytes_per_pixel;
    if (msg.step < min_step) {
      throw std::runtime_error("Image step is smaller than width * bytes_per_pixel.");
    }

    const size_t min_data_size =
      static_cast<size_t>(msg.step) * static_cast<size_t>(msg.height - 1) + min_step;
    if (msg.data.size() < min_data_size) {
      throw std::runtime_error("Image data buffer is smaller than expected from width/height/step.");
    }

    return cv::Mat(
      static_cast<int>(msg.height),
      static_cast<int>(msg.width),
      type,
      const_cast<unsigned char *>(msg.data.data()),
      static_cast<size_t>(msg.step)).clone();
  }

  int queue_size_{10};
  double sync_slop_seconds_{0.15};
  std::string output_dir_{"."};
  std::mutex shutdown_mutex_;
  std::atomic_bool shutdown_started_{false};
  std::atomic_size_t frame_count_{0};

  std::unique_ptr<ORB_SLAM2::System> slam_;
  message_filters::Subscriber<ImageMsg> rgb_sub_;
  message_filters::Subscriber<ImageMsg> depth_sub_;
  std::shared_ptr<Synchronizer> sync_;
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr cmd_sub_;
};

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);

  try {
    auto node = std::make_shared<RGBDNode>();
    rclcpp::spin(node);
    node->shutdownSlam();
  } catch (const std::exception &ex) {
    std::cerr << "orbslam2_pointcloud_ros2 failed: " << ex.what() << std::endl;
    rclcpp::shutdown();
    return 1;
  }

  if (rclcpp::ok()) {
    rclcpp::shutdown();
  }
  return 0;
}
