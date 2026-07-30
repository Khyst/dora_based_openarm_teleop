#include <atomic>
#include <fstream>
#include <memory>
#include <moveit/move_group_interface/move_group_interface.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sstream>
#include <std_msgs/msg/string.hpp>
#include "openarm_motion/srv/execute_sequence.hpp"
#include <string>
#include <thread>
#include <vector>

struct MotionStep {
  std::string group;
  std::string pose;
};

class MotionActionServer : public rclcpp::Node {
public:
  MotionActionServer() : Node("motion_action_server") {
    // Declare parameter for JSON file path
    this->declare_parameter<std::string>("json_file_path", "");
    this->declare_parameter<std::string>("json_dir", "");

    // Create the Service Server
    service_ = this->create_service<openarm_motion::srv::ExecuteSequence>(
        "execute_sequence",
        std::bind(&MotionActionServer::trigger_callback, this,
                  std::placeholders::_1, std::placeholders::_2));

    // Create the Publishers for Hamsa hand commands
    hamsa_pub_ = this->create_publisher<std_msgs::msg::String>("/hamsa/pose_command", 10);
    right_hamsa_pub_ = this->create_publisher<std_msgs::msg::String>("/right_hamsa/pose_command", 10);
    left_hamsa_pub_ = this->create_publisher<std_msgs::msg::String>("/left_hamsa/pose_command", 10);

    RCLCPP_INFO(this->get_logger(),
                "Motion Action Server Service /execute_sequence is ready.");
  }

  private:
  void trigger_callback(
      const std::shared_ptr<openarm_motion::srv::ExecuteSequence::Request> request,
      std::shared_ptr<openarm_motion::srv::ExecuteSequence::Response> response) {
    std::string file_path = request->file_name;
    if (file_path.empty()) {
      this->get_parameter("json_file_path", file_path);
    } else {
      // If it doesn't end with .json, append it
      if (file_path.size() < 5 || file_path.compare(file_path.size() - 5, 5, ".json") != 0) {
        file_path += ".json";
      }

      if (file_path[0] != '/') {
        std::string json_dir;
        this->get_parameter("json_dir", json_dir);
        file_path = json_dir + "/" + file_path;
      }
    }

    if (is_running_) {
      response->success = false;
      response->message = "Motion sequence is already running!";
      return;
    }

    // Spawn a detached thread to run the motion sequence without blocking the
    // ROS 2 executor
    std::thread([this, file_path]() { this->execute_sequence(file_path); }).detach();

    response->success = true;
    response->message = "Motion sequence triggered successfully with file: " + file_path;
  }

  void execute_sequence(const std::string &file_path) {
    is_running_ = true;
    RCLCPP_INFO(this->get_logger(), "Starting motion sequence execution using file: %s", file_path.c_str());

    if (file_path.empty()) {
      RCLCPP_ERROR(this->get_logger(),
                   "JSON file path is empty!");
      is_running_ = false;
      return;
    }

    auto steps = parse_motion_json(file_path);
    if (steps.empty()) {
      RCLCPP_ERROR(this->get_logger(), "No steps parsed from JSON file: %s",
                   file_path.c_str());
      is_running_ = false;
      return;
    }

    RCLCPP_INFO(this->get_logger(), "Loaded %zu motion steps from JSON.",
                steps.size());

    auto left_arm_group =
        std::make_shared<moveit::planning_interface::MoveGroupInterface>(
            shared_from_this(), "left_arm");
    auto right_arm_group =
        std::make_shared<moveit::planning_interface::MoveGroupInterface>(
            shared_from_this(), "right_arm");

    // -----------------------------------------------------------------
    // [개선 포인트] 연속된 동일 그룹의 스텝들을 묶어서 처리하기 위한 루프
    // -----------------------------------------------------------------
    size_t i = 0;
    while (i < steps.size()) {
      std::string current_group_name = steps[i].group;
      std::shared_ptr<moveit::planning_interface::MoveGroupInterface>
          target_group;

      if (current_group_name == "hamsa") {
        std_msgs::msg::String msg;
        msg.data = steps[i].pose;
        RCLCPP_INFO(this->get_logger(), "Publishing hamsa hand pose command (both hands): '%s'",
                    msg.data.c_str());
        hamsa_pub_->publish(msg);

        // [Caution] Sleep to allow hand wiggling/curling to complete
        std::this_thread::sleep_for(std::chrono::milliseconds(3000));
        i++;
        continue;
      }

      if (current_group_name == "right" || current_group_name == "right_hamsa") {
        std_msgs::msg::String msg;
        msg.data = steps[i].pose;
        RCLCPP_INFO(this->get_logger(), "Publishing right hamsa hand pose command: '%s'",
                    msg.data.c_str());
        right_hamsa_pub_->publish(msg);

        // [Caution] Sleep to allow hand wiggling/curling to complete
        std::this_thread::sleep_for(std::chrono::milliseconds(3000));
        i++;
        continue;
      }

      if (current_group_name == "left" || current_group_name == "left_hamsa") {
        std_msgs::msg::String msg;
        msg.data = steps[i].pose;
        RCLCPP_INFO(this->get_logger(), "Publishing left hamsa hand pose command: '%s'",
                    msg.data.c_str());
        left_hamsa_pub_->publish(msg);

        // [Caution] Sleep to allow hand wiggling/curling to complete
        std::this_thread::sleep_for(std::chrono::milliseconds(3000));
        i++;
        continue;
      }

      if (current_group_name == "left_arm") {
        target_group = left_arm_group;
      } else if (current_group_name == "right_arm") {
        target_group = right_arm_group;
      } else {
        RCLCPP_WARN(this->get_logger(), "Unknown group: %s. Skipping.",
                    current_group_name.c_str());
        i++;
        continue;
      }

      // 현재 그룹에서 연속으로 처리할 수 있는 Named Pose들을 수집합니다.
      std::vector<std::string> consecutive_poses;
      while (i < steps.size() && steps[i].group == current_group_name) {
        consecutive_poses.push_back(steps[i].pose);
        i++;
      }

      // -----------------------------------------------------------------
      // [해결책 A 적용] Hamsa 핸드 동작 종료 후 센서 피드백 동기화 및 
      // 시작 상태 명시적 업데이트를 위한 대기 시간 추가
      // -----------------------------------------------------------------
      RCLCPP_INFO(this->get_logger(), 
                  "Waiting 200ms to allow joint state feedback to synchronize...");
      std::this_thread::sleep_for(std::chrono::milliseconds(200));

      RCLCPP_INFO(
          this->get_logger(),
          "Planning merged trajectory for group '%s' with %zu waypoints.",
          current_group_name.c_str(), consecutive_poses.size());

      // 통합할 메인 Plan 객체 생성
      moveit::planning_interface::MoveGroupInterface::Plan merged_plan;
      bool first_plan_combined = false;

      auto robot_model = target_group->getRobotModel();
      target_group->setStartStateToCurrentState(); // MoveGroup 내부의 시작 상태 최신화
      moveit::core::RobotState start_state(*target_group->getCurrentState());

      for (const auto &pose_name : consecutive_poses) {
        // 1. 목표 Named Pose 설정
        target_group->setStartState(start_state);
        target_group->setNamedTarget(pose_name);

        // 2. 단일 스텝 Plan 계산
        moveit::planning_interface::MoveGroupInterface::Plan sub_plan;
        auto plan_result = target_group->plan(sub_plan);

        if (plan_result == moveit::core::MoveItErrorCode::SUCCESS) {
          if (!first_plan_combined) {
            // 첫 번째 가고자 하는 궤적은 그대로 복사
            merged_plan = sub_plan;
            first_plan_combined = true;
          } else {
            // 두 번째 궤적부터는 기존 궤적 뒤에 포인트를 이어 붙임 (시간 축
            // 오프셋 계산)
            auto &merged_traj = merged_plan.trajectory.joint_trajectory;
            const auto &sub_traj = sub_plan.trajectory.joint_trajectory;

            if (!merged_traj.points.empty() && !sub_traj.points.empty()) {
              // 이전 궤적의 마지막 타임스탬프를 기준으로 누적 시간 계산
              rclcpp::Duration last_time_duration =
                  merged_traj.points.back().time_from_start;

              // 첫 포인트는 중복되므로 제외하고 2번째 포인트부터 병합
              for (size_t p_idx = 1; p_idx < sub_traj.points.size(); ++p_idx) {
                auto point = sub_traj.points[p_idx];
                // 타임스탬프 누적 보정
                point.time_from_start =
                    last_time_duration +
                    rclcpp::Duration(sub_traj.points[p_idx].time_from_start);
                merged_traj.points.push_back(point);
              }
            }
          }

          // 다음 Waypoint의 시작 상태를 현재 계산된 Plan의 마지막 상태로
          // 업데이트 (연속성 유지)
          if (!sub_plan.trajectory.joint_trajectory.points.empty()) {
            const auto &last_point =
                sub_plan.trajectory.joint_trajectory.points.back();
            start_state.setJointGroupPositions(current_group_name,
                                               last_point.positions);
          }

        } else {
          RCLCPP_ERROR(this->get_logger(),
                       "Failed to plan for pose '%s'. Aborting group sequence.",
                       pose_name.c_str());
          first_plan_combined = false;
          break;
        }
      }

      // 3. 병합된 하나의 거대한 궤적을 끊김 없이 일괄 실행
      if (first_plan_combined &&
          !merged_plan.trajectory.joint_trajectory.points.empty()) {
        RCLCPP_INFO(this->get_logger(),
                    "Executing smoothly merged trajectory...");

        // 시간 파라미터 재조정(Time Parameterization) 프로세스를 거치면 더욱
        // 부드러워집니다. 여기서는 단순 병합 후 바로 execute를 수행합니다.
        const auto code = target_group->execute(merged_plan);

        if (code) {
          RCLCPP_INFO(this->get_logger(),
                      "Merged trajectory execution SUCCESS.");
        } else {
          RCLCPP_ERROR(this->get_logger(),
                       "Merged trajectory execution FAILED with error code %d",
                       code.val);
          break;
        }
      }

      if (i < steps.size()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
      }
    }

    RCLCPP_INFO(this->get_logger(), "Motion sequence execution finished.");
    is_running_ = false;
  }

  std::vector<MotionStep> parse_motion_json(const std::string &file_path) {
    std::vector<MotionStep> steps;
    std::ifstream file(file_path);
    if (!file.is_open()) {
      return steps;
    }

    std::string line;
    std::string full_content;
    while (std::getline(file, line)) {
      full_content += line;
    }

    size_t pos = 0;
    while (true) {
      size_t start_obj = full_content.find("{", pos);
      if (start_obj == std::string::npos)
        break;
      size_t end_obj = full_content.find("}", start_obj);
      if (end_obj == std::string::npos)
        break;

      std::string obj_str =
          full_content.substr(start_obj, end_obj - start_obj + 1);

      size_t group_key = obj_str.find("\"group\"");
      size_t group_val_start = obj_str.find("\"", group_key + 7);
      size_t group_val_end = obj_str.find("\"", group_val_start + 1);
      std::string group = obj_str.substr(group_val_start + 1,
                                         group_val_end - group_val_start - 1);

      size_t pose_key = obj_str.find("\"pose\"");
      size_t pose_val_start = obj_str.find("\"", pose_key + 6);
      size_t pose_val_end = obj_str.find("\"", pose_val_start + 1);
      std::string pose =
          obj_str.substr(pose_val_start + 1, pose_val_end - pose_val_start - 1);

      if (!group.empty() && !pose.empty()) {
        steps.push_back({group, pose});
      }

      pos = end_obj + 1;
    }
    return steps;
  }

  rclcpp::Service<openarm_motion::srv::ExecuteSequence>::SharedPtr service_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr hamsa_pub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr right_hamsa_pub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr left_hamsa_pub_;
  std::atomic<bool> is_running_{false};
};

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);

  auto node = std::make_shared<MotionActionServer>();

  // A MultiThreadedExecutor is REQUIRED so MoveGroup planning callbacks can
  // execute in parallel
  rclcpp::executors::MultiThreadedExecutor executor;
  executor.add_node(node);
  executor.spin();

  rclcpp::shutdown();
  return 0;
}
