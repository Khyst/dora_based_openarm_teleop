#!/usr/bin/env python3

import os
import sys
import threading
import time

from hamsa import left, right, hand as right_hand_compat
from hamsa import firmware

# ---------------------------------------------------------
# 2. Implement ROS 2 Node
# ---------------------------------------------------------
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class HamsaMotionNode(Node):

    def __init__(self):
        super().__init__('hamsa_motion_node')
        
        # Declare parameters
        self.declare_parameter('command_topic', '/hamsa/pose_command')
        self.declare_parameter('right_command_topic', '/right_hamsa/pose_command')
        self.declare_parameter('left_command_topic', '/left_hamsa/pose_command')
        
        self.declare_parameter('close_duration_ms', 500)
        self.declare_parameter('open_duration_ms', 500)
        self.declare_parameter('grab_duration_ms', 500)
        self.declare_parameter('release_duration_ms', 500)
        self.declare_parameter('scissor_duration_ms', 500)

        compat_topic = self.get_parameter('command_topic').get_parameter_value().string_value
        right_topic = self.get_parameter('right_command_topic').get_parameter_value().string_value
        left_topic = self.get_parameter('left_command_topic').get_parameter_value().string_value
        
        self.get_logger().info(f"Initializing HamsaMotionNode...")
        self.get_logger().info(f" -> Backwards compatibility topic: '{compat_topic}' (controls Right Hand)")
        self.get_logger().info(f" -> Right Hand topic: '{right_topic}'")
        self.get_logger().info(f" -> Left Hand topic: '{left_topic}'")
        
        # Backwards compatibility subscriber (Right Hand)
        self.compat_subscription = self.create_subscription(
            String,
            compat_topic,
            self.compat_command_callback,
            10
        )

        # Right Hand subscriber
        self.right_subscription = self.create_subscription(
            String,
            right_topic,
            self.right_command_callback,
            10
        )

        # Left Hand subscriber
        self.left_subscription = self.create_subscription(
            String,
            left_topic,
            self.left_command_callback,
            10
        )
        
        # Map received string commands to local motion functions (accepting hand_obj)
        self.commands_map = {
            'close_palm': self.close_palm,
            'open_palm': self.open_palm,
            'grab': self.grab,
            'release': self.release,
            'scissor': self.scissor
        }
        
        # Separate mutexes and status to support concurrent, non-blocking movement for both hands
        self.right_mutex = threading.Lock()
        self.left_mutex = threading.Lock()
        
        self.right_active_command = None
        self.left_active_command = None
        
        self.right_thread = None
        self.left_thread = None

        self.initial_hand_pose()
        
        self.get_logger().info("HamsaMotionNode is ready.")

    # ---------------------------------------------------------
    # Hamsa hand-motion functions
    # ---------------------------------------------------------

    def initial_hand_pose(self):
        self.get_logger().info("Executing initial_hand_pose for Right and Left hands...")
        self.init_single_hand(right)
        self.init_single_hand(left)

    def init_single_hand(self, hand_obj):
        # hand_obj.wiggle_pinky(0.5, 1000)
        # hand_obj.wiggle_ring(0.5, 1000)
        # hand_obj.wiggle_middle(0.5, 1000)
        # hand_obj.wiggle_index(0.5, 1000)
        # hand_obj.wiggle_thumb(0.5, 1000)

        # fully curled for release
        hand_obj.curl_pinky(0.9, 2000) 
        hand_obj.curl_ring(0.9, 2000)
        hand_obj.curl_middle(0.9, 2000)
        hand_obj.curl_index(0.9, 2000)
        hand_obj.curl_thumb(0.9, 2000)
        
    # 좁히기 (Close)
    def close_palm(self, hand_obj):
        duration = self.get_parameter('close_duration_ms').get_parameter_value().integer_value
        index_duration = int(duration / 2)
        
        self.get_logger().info(f"Executing close_palm on {hand_obj.side} hand (duration: {duration} ms)")
        hand_obj.wiggle_pinky(0, duration)
        hand_obj.wiggle_ring(0, duration)
        hand_obj.wiggle_middle(1, duration)
        hand_obj.wiggle_index(1, index_duration)
        hand_obj.wiggle_thumb(1, duration)

    # 펼치기 (Open)
    def open_palm(self, hand_obj):
        duration = self.get_parameter('open_duration_ms').get_parameter_value().integer_value
        index_duration = int(duration / 2)
        
        self.get_logger().info(f"Executing open_palm on {hand_obj.side} hand (duration: {duration} ms)")
        hand_obj.wiggle_pinky(1, duration)
        hand_obj.wiggle_ring(1, duration)
        hand_obj.wiggle_middle(0, duration)
        hand_obj.wiggle_index(0, index_duration)
        hand_obj.wiggle_thumb(0, duration)

    # 구부리기 (Grab)
    def grab(self, hand_obj):
        duration = self.get_parameter('grab_duration_ms').get_parameter_value().integer_value
        
        self.get_logger().info(f"Executing grab on {hand_obj.side} hand (duration: {duration} ms)")
        hand_obj.curl_pinky(0, duration)
        hand_obj.curl_ring(0, duration)
        hand_obj.curl_middle(0, duration)
        hand_obj.curl_index(0, duration)
        hand_obj.curl_thumb(0, duration)

    # 펼치기 (Release)
    def release(self, hand_obj):
        duration = self.get_parameter('release_duration_ms').get_parameter_value().integer_value
        thumb_duration = int(duration * 0.9)
        
        self.get_logger().info(f"Executing release on {hand_obj.side} hand (duration: {duration} ms)")
        hand_obj.curl_pinky(1, duration)
        hand_obj.curl_ring(1, duration)
        hand_obj.curl_middle(1, duration)
        hand_obj.curl_index(1, duration)
        hand_obj.curl_thumb(1, thumb_duration)

    # 가위 (Scissor)
    def scissor(self, hand_obj):
        duration = self.get_parameter('scissor_duration_ms').get_parameter_value().integer_value
        
        self.get_logger().info(f"Executing scissor on {hand_obj.side} hand (duration: {duration} ms)")
        hand_obj.curl_pinky(0, duration)
        hand_obj.curl_ring(0, duration)
        hand_obj.curl_thumb(0, duration)
        hand_obj.curl_middle(1, duration)
        hand_obj.curl_index(1, duration)

    # ---------------------------------------------------------
    # Subscribers Callbacks
    # ---------------------------------------------------------

    def compat_command_callback(self, msg):
        self.get_logger().info(f"Received compatibility/both-hands command '{msg.data}' on topic '/hamsa/pose_command'")
        self.handle_command(msg.data, right, self.right_mutex, 'right')
        self.handle_command(msg.data, left, self.left_mutex, 'left')

    def right_command_callback(self, msg):
        self.handle_command(msg.data, right, self.right_mutex, 'right')

    def left_command_callback(self, msg):
        self.handle_command(msg.data, left, self.left_mutex, 'left')

    def handle_command(self, raw_data, hand_obj, mutex, side):
        command = raw_data.strip().lower()
        self.get_logger().info(f"Received command '{command}' for {side} hand")

        if command not in self.commands_map:
            self.get_logger().warning(
                f"Unknown command '{command}' for {side} hand. Supported: {list(self.commands_map.keys())}"
            )
            return

        # Check if the hand is already executing a command
        if not mutex.acquire(blocking=False):
            active_cmd = self.right_active_command if side == 'right' else self.left_active_command
            self.get_logger().warning(
                f"Ignored command '{command}' for {side} hand: Busy executing '{active_cmd}'."
            )
            return

        # Assign active command status and release standard lock so callbacks don't block
        if side == 'right':
            self.right_active_command = command
        else:
            self.left_active_command = command
        mutex.release()

        # Execute the motion function inside a separate worker thread
        t = threading.Thread(
            target=self.execute_motion_thread,
            args=(command, hand_obj, mutex, side),
            daemon=True
        )
        if side == 'right':
            self.right_thread = t
        else:
            self.left_thread = t
        t.start()

    def execute_motion_thread(self, command, hand_obj, mutex, side):
        # Acquire lock to ensure only one thread executes motion on this hand at a time
        with mutex:
            self.get_logger().info(f"Starting execution of motion '{command}' on {side} hand")
            motion_func = self.commands_map[command]
            try:
                motion_func(hand_obj)
                self.get_logger().info(f"Successfully completed motion '{command}' on {side} hand")
            except Exception as e:
                self.get_logger().error(f"Failed to execute motion '{command}' on {side} hand: {e}")
            finally:
                if side == 'right':
                    self.right_active_command = None
                else:
                    self.left_active_command = None

def main(args=None):
    rclpy.init(args=args)
    node = HamsaMotionNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("HamsaMotionNode shutting down via keyboard interrupt.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
