#!/usr/bin/env python3

import os
import json
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from sensor_msgs.msg import JointState
from std_srvs.srv import Trigger, SetBool
from openarm_motion.srv import ExecuteSequence
from controller_manager_msgs.srv import SwitchController
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import FollowJointTrajectory

class MotionTeachingNode(Node):
    def __init__(self):
        super().__init__("motion_teaching_node")

        # Reentrant callback group to allow nested service calls and concurrent executions
        self.cb_group = ReentrantCallbackGroup()

        # Declare parameters
        self.declare_parameter("json_dir", "/home/khy/5.nana_openarm_container_ws/src/researches/openarm_motion/json")
        self.json_dir = self.get_parameter("json_dir").get_parameter_value().string_value

        self.is_recording = False
        self.left_points = []
        self.right_points = []
        self.start_time = None
        self.last_record_time = 0.0

        self.left_joint_names = [f"nana_v3_left_joint{i}" for i in range(1, 8)]
        self.right_joint_names = [f"nana_v3_right_joint{i}" for i in range(1, 8)]

        # Services
        self.start_srv = self.create_service(
            Trigger, "/motion_teaching/start_recording", self.start_recording_callback,
            callback_group=self.cb_group
        )
        self.stop_srv = self.create_service(
            ExecuteSequence, "/motion_teaching/stop_recording", self.stop_recording_callback,
            callback_group=self.cb_group
        )
        self.play_srv = self.create_service(
            ExecuteSequence, "/motion_teaching/playback", self.playback_callback,
            callback_group=self.cb_group
        )

        # Subscription to JointState
        self.js_sub = self.create_subscription(
            JointState, "/joint_states", self.joint_states_callback, 10,
            callback_group=self.cb_group
        )

        self.get_logger().info("Motion Teaching Node has been initialized.")
        self.get_logger().info(f"Target directory for saved trajectories: {self.json_dir}")

    def start_recording_callback(self, request, response):
        if self.is_recording:
            response.success = False
            response.message = "Already recording!"
            return response

        self.get_logger().info("Starting motion recording...")

        # 1. Switch controllers off to allow manual moving safely
        self.switch_controllers(deactivate=["left_joint_trajectory_controller", "right_joint_trajectory_controller"])

        # 2. Call hardware services to set TEACH (gravity compensation) mode
        self.set_hardware_mode("left", True)
        self.set_hardware_mode("right", True)

        # 3. Reset buffers
        self.left_points = []
        self.right_points = []
        self.start_time = self.get_clock().now()
        self.last_record_time = 0.0
        self.is_recording = True

        response.success = True
        response.message = "Recording started successfully. Move the arms freely!"
        return response

    def stop_recording_callback(self, request, response):
        if not self.is_recording:
            response.success = False
            response.message = "Not currently recording!"
            return response

        self.is_recording = False
        self.get_logger().info("Stopping motion recording...")

        # 1. Save data to JSON file
        file_name = request.file_name
        if not file_name:
            file_name = f"teaching_{int(time.time())}.json"

        if not file_name.endswith(".json"):
            file_name += ".json"

        if file_name.startswith("/"):
            full_path = file_name
        else:
            full_path = os.path.join(self.json_dir, file_name)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        data = {
            "left_arm": {
                "joint_names": self.left_joint_names,
                "points": self.left_points
            },
            "right_arm": {
                "joint_names": self.right_joint_names,
                "points": self.right_points
            }
        }

        try:
            with open(full_path, "w") as f:
                json.dump(data, f, indent=2)
            self.get_logger().info(f"Trajectory saved to {full_path}")
            save_success = True
            save_message = f"Saved to {full_path}"
        except Exception as e:
            self.get_logger().error(f"Failed to save JSON: {str(e)}")
            save_success = False
            save_message = f"Failed to save file: {str(e)}"

        # 2. Call hardware services to restore POSITION mode
        self.set_hardware_mode("left", False)
        self.set_hardware_mode("right", False)

        # 3. Switch controllers back on
        self.switch_controllers(activate=["left_joint_trajectory_controller", "right_joint_trajectory_controller"])

        response.success = save_success
        response.message = save_message
        return response

    def joint_states_callback(self, msg):
        if not self.is_recording:
            return

        now = self.get_clock().now()
        if self.start_time is None:
            self.start_time = now
        elapsed_ns = (now - self.start_time).nanoseconds
        elapsed_sec = elapsed_ns / 1e9

        # Downsample to 20Hz (0.05s interval)
        if elapsed_sec - self.last_record_time < 0.05:
            return
        self.last_record_time = elapsed_sec

        # Filter joint state positions and velocities
        left_pos = [None] * 7
        left_vel = [None] * 7
        right_pos = [None] * 7
        right_vel = [None] * 7

        for i, name in enumerate(msg.name):
            if name in self.left_joint_names:
                idx = self.left_joint_names.index(name)
                left_pos[idx] = msg.position[i]
                if len(msg.velocity) > i:
                    left_vel[idx] = msg.velocity[i]
            elif name in self.right_joint_names:
                idx = self.right_joint_names.index(name)
                right_pos[idx] = msg.position[i]
                if len(msg.velocity) > i:
                    right_vel[idx] = msg.velocity[i]

        # Ensure we have all values
        if all(p is not None for p in left_pos):
            self.left_points.append({
                "positions": left_pos,
                "velocities": [v if v is not None else 0.0 for v in left_vel],
                "time_from_start": elapsed_sec
            })

        if all(p is not None for p in right_pos):
            self.right_points.append({
                "positions": right_pos,
                "velocities": [v if v is not None else 0.0 for v in right_vel],
                "time_from_start": elapsed_sec
            })

    def switch_controllers(self, activate=[], deactivate=[]):
        client = self.create_client(
            SwitchController,
            "/controller_manager/switch_controller",
            callback_group=self.cb_group
        )
        if not client.wait_for_service(timeout_sec=2.0):
            self.get_logger().warn("SwitchController service not available. Skipping controller switch.")
            return False

        req = SwitchController.Request()
        req.activate_controllers = activate
        req.deactivate_controllers = deactivate
        req.strictness = SwitchController.Request.STRICT
        req.activate_asap = True

        future = client.call_async(req)

        # Wait for the future to complete since the executor is spinning on other threads
        start_time = self.get_clock().now()
        timeout = rclpy.duration.Duration(seconds=3.0)
        while not future.done():
            time.sleep(0.01)
            if (self.get_clock().now() - start_time) > timeout:
                self.get_logger().error("SwitchController call timed out.")
                return False

        try:
            res = future.result()
            if res and res.ok:
                self.get_logger().info(f"Switched controllers: activated={activate}, deactivated={deactivate}")
                return True
            else:
                self.get_logger().error("Failed to switch controllers.")
                return False
        except Exception as e:
            self.get_logger().error(f"SwitchController call exception: {str(e)}")
            return False

    def set_hardware_mode(self, arm, enable_teach):
        service_name = f"/nana_v3_hardware/{arm}/set_mode"
        client = self.create_client(
            SetBool,
            service_name,
            callback_group=self.cb_group
        )
        if not client.wait_for_service(timeout_sec=2.0):
            self.get_logger().warn(f"Hardware set_mode service for {arm} arm not available. Skipping.")
            return False

        req = SetBool.Request()
        req.data = enable_teach
        future = client.call_async(req)

        # Wait for the future to complete
        start_time = self.get_clock().now()
        timeout = rclpy.duration.Duration(seconds=3.0)
        while not future.done():
            time.sleep(0.01)
            if (self.get_clock().now() - start_time) > timeout:
                self.get_logger().error(f"Hardware set_mode call for {arm} arm timed out.")
                return False

        try:
            res = future.result()
            if res and res.success:
                self.get_logger().info(f"Hardware mode for {arm} arm set to {'TEACH' if enable_teach else 'POSITION'}: {res.message}")
                return True
            else:
                self.get_logger().error(f"Failed to set hardware mode for {arm} arm: {res.message if res else 'None'}")
                return False
        except Exception as e:
            self.get_logger().error(f"Hardware set_mode call exception: {str(e)}")
            return False

    def playback_callback(self, request, response):
        if self.is_recording:
            response.success = False
            response.message = "Cannot play back while recording!"
            return response

        file_name = request.file_name
        if not file_name:
            response.success = False
            response.message = "Filename is empty!"
            return response

        if not file_name.endswith(".json"):
            file_name += ".json"

        if file_name.startswith("/"):
            full_path = file_name
        else:
            full_path = os.path.join(self.json_dir, file_name)

        if not os.path.exists(full_path):
            response.success = False
            response.message = f"File {full_path} does not exist!"
            return response

        try:
            with open(full_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            response.success = False
            response.message = f"Failed to load/parse JSON: {str(e)}"
            return response

        self.get_logger().info(f"Playing back trajectory from {full_path}...")

        # Switch to POSITION mode and activate controllers if needed
        self.set_hardware_mode("left", False)
        self.set_hardware_mode("right", False)
        self.switch_controllers(activate=["left_joint_trajectory_controller", "right_joint_trajectory_controller"])

        # Construct Action clients and goals
        left_client = ActionClient(
            self,
            FollowJointTrajectory,
            "/left_joint_trajectory_controller/follow_joint_trajectory",
            callback_group=self.cb_group
        )
        right_client = ActionClient(
            self,
            FollowJointTrajectory,
            "/right_joint_trajectory_controller/follow_joint_trajectory",
            callback_group=self.cb_group
        )

        left_goal = None
        right_goal = None

        if "left_arm" in data and data["left_arm"]["points"]:
            left_goal = self.create_trajectory_goal(data["left_arm"])
        if "right_arm" in data and data["right_arm"]["points"]:
            right_goal = self.create_trajectory_goal(data["right_arm"])

        # Send goals in parallel
        futures = []
        if left_goal and left_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().info("Sending left arm trajectory...")
            futures.append((left_client.send_goal_async(left_goal), "left"))
        if right_goal and right_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().info("Sending right arm trajectory...")
            futures.append((right_client.send_goal_async(right_goal), "right"))

        if not futures:
            response.success = False
            response.message = "No valid trajectories sent to action servers."
            return response

        # Wait for goal handles
        goal_handles = {}
        for future, arm in futures:
            start_time = self.get_clock().now()
            timeout = rclpy.duration.Duration(seconds=5.0)
            while not future.done():
                time.sleep(0.01)
                if (self.get_clock().now() - start_time) > timeout:
                    self.get_logger().error(f"Goal response for {arm} arm timed out.")
                    break
            if future.done():
                handle = future.result()
                if handle and handle.accepted:
                    self.get_logger().info(f"Trajectory goal accepted for {arm} arm.")
                    goal_handles[arm] = handle
                else:
                    self.get_logger().error(f"Trajectory goal rejected for {arm} arm.")

        if not goal_handles:
            response.success = False
            response.message = "Trajectory goals were rejected by the controllers."
            return response

        # Get results
        result_futures = []
        for arm, handle in goal_handles.items():
            result_futures.append((handle.get_result_async(), arm))

        # Wait for all results
        success = True
        messages = []
        for future, arm in result_futures:
            start_time = self.get_clock().now()
            timeout = rclpy.duration.Duration(seconds=60.0)
            while not future.done():
                time.sleep(0.01)
                if (self.get_clock().now() - start_time) > timeout:
                    self.get_logger().error(f"Goal result for {arm} arm timed out.")
                    break
            if future.done():
                result = future.result()
                if result and result.status == 4: # GoalStatus.STATUS_SUCCEEDED
                    self.get_logger().info(f"Playback succeeded for {arm} arm.")
                    messages.append(f"{arm}: Success")
                else:
                    self.get_logger().error(f"Playback failed/cancelled for {arm} arm. Status: {result.status if result else 'None'}")
                    success = False
                    messages.append(f"{arm}: Failed/Cancelled")
            else:
                success = False
                messages.append(f"{arm}: Timeout")

        response.success = success
        response.message = ", ".join(messages)
        return response

    def create_trajectory_goal(self, arm_data):
        goal = FollowJointTrajectory.Goal()
        traj = JointTrajectory()
        traj.joint_names = arm_data["joint_names"]

        for pt in arm_data["points"]:
            point = JointTrajectoryPoint()
            point.positions = pt["positions"]
            if "velocities" in pt:
                point.velocities = pt["velocities"]

            # Construct time_from_start
            t = pt["time_from_start"]
            sec = int(t)
            nanosec = int((t - sec) * 1e9)
            point.time_from_start.sec = sec
            point.time_from_start.nanosec = nanosec
            traj.points.append(point)

        goal.trajectory = traj
        return goal

def main(args=None):
    rclpy.init(args=args)
    node = MotionTeachingNode()
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
