cmake_minimum_required(VERSION 3.8)
project(openarm_motion)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic -std=c++17)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Generate custom service interface
rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/ExecuteSequence.srv"
)

# Add the main motion server executable
add_executable(motion_action_server src/motion_action_server.cpp)
target_include_directories(motion_action_server PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(motion_action_server
  rclcpp
  rclcpp_action
  moveit_ros_planning_interface
  std_msgs
  std_srvs
)

# Add the motion server with joint states sync executable
add_executable(motion_action_server_joint_states_sync src/motion_action_server_joint_states_sync.cpp)
target_include_directories(motion_action_server_joint_states_sync PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(motion_action_server_joint_states_sync
  rclcpp
  rclcpp_action
  moveit_ros_planning_interface
  std_msgs
  std_srvs
)

# Link typesupport targets for internal service headers
rosidl_get_typesupport_target(cpp_typesupport_target "${PROJECT_NAME}" "rosidl_typesupport_cpp")
target_link_libraries(motion_action_server "${cpp_typesupport_target}")
target_link_libraries(motion_action_server_joint_states_sync "${cpp_typesupport_target}")

# Install executable targets
install(TARGETS 
  motion_action_server
  motion_action_server_joint_states_sync
  DESTINATION lib/${PROJECT_NAME}
)

# Install the JSON motion configurations folder so it's in share directory
install(DIRECTORY json/
  DESTINATION share/${PROJECT_NAME}/json
)

# Install launch files
install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

# Install configuration parameters
install(DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
)

# Install the python teaching node
install(PROGRAMS
  src/motion_teaching_node.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
