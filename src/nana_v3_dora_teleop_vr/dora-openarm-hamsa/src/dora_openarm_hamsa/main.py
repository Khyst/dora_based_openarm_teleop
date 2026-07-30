#!/usr/bin/env python3

import logging
import threading
import dora

try:
    from hamsa import left, right
except ImportError:
    left, right = None, None

logging.basicConfig(level=logging.INFO, format="[dora-openarm-hamsa] %(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class HamsaMotionController:
    def __init__(self):
        self.right_mutex = threading.Lock()
        self.left_mutex = threading.Lock()

        self.right_active_command = None
        self.left_active_command = None

        self.right_state = "release"
        self.left_state = "release"

        self.right_thread = None
        self.left_thread = None

        self.close_duration_ms = 500
        self.open_duration_ms = 500
        self.grab_duration_ms = 500
        self.release_duration_ms = 500
        self.scissor_duration_ms = 500

        self.commands_map = {
            "close_palm": self.close_palm,
            "open_palm": self.open_palm,
            "grab": self.grab,
            "release": self.release,
            "scissor": self.scissor,
        }

        self.initial_hand_pose()
        logger.info("HamsaMotionController initialized.")

    def initial_hand_pose(self):
        logger.info("Executing initial_hand_pose for Right and Left hands...")
        if right is not None:
            self.init_single_hand(right)
        else:
            logger.warning("Right hand object unavailable.")

        if left is not None:
            self.init_single_hand(left)
        else:
            logger.warning("Left hand object unavailable.")

    def init_single_hand(self, hand_obj):
        try:
            hand_obj.curl_pinky(0.9, 2000)
            hand_obj.curl_ring(0.9, 2000)
            hand_obj.curl_middle(0.9, 2000)
            hand_obj.curl_index(0.9, 2000)
            hand_obj.curl_thumb(0.9, 2000)
        except Exception as e:
            side_str = getattr(hand_obj, "side", "unknown")
            logger.error(f"Failed to init_single_hand for {side_str} hand: {e}")

    def close_palm(self, hand_obj):
        duration = self.close_duration_ms
        index_duration = int(duration / 2)
        side_str = getattr(hand_obj, "side", "unknown")
        logger.info(f"Executing close_palm on {side_str} hand (duration: {duration} ms)")
        hand_obj.wiggle_pinky(0, duration)
        hand_obj.wiggle_ring(0, duration)
        hand_obj.wiggle_middle(1, duration)
        hand_obj.wiggle_index(1, index_duration)
        hand_obj.wiggle_thumb(1, duration)

    def open_palm(self, hand_obj):
        duration = self.open_duration_ms
        index_duration = int(duration / 2)
        side_str = getattr(hand_obj, "side", "unknown")
        logger.info(f"Executing open_palm on {side_str} hand (duration: {duration} ms)")
        hand_obj.wiggle_pinky(1, duration)
        hand_obj.wiggle_ring(1, duration)
        hand_obj.wiggle_middle(0, duration)
        hand_obj.wiggle_index(0, index_duration)
        hand_obj.wiggle_thumb(0, duration)

    def grab(self, hand_obj):
        duration = self.grab_duration_ms
        side_str = getattr(hand_obj, "side", "unknown")
        logger.info(f"Executing grab on {side_str} hand (duration: {duration} ms)")
        hand_obj.curl_pinky(0, duration)
        hand_obj.curl_ring(0, duration)
        hand_obj.curl_middle(0, duration)
        hand_obj.curl_index(0, duration)
        hand_obj.curl_thumb(0, duration)

    def release(self, hand_obj):
        duration = self.release_duration_ms
        thumb_duration = int(duration * 0.9)
        side_str = getattr(hand_obj, "side", "unknown")
        logger.info(f"Executing release on {side_str} hand (duration: {duration} ms)")
        hand_obj.curl_pinky(1, duration)
        hand_obj.curl_ring(1, duration)
        hand_obj.curl_middle(1, duration)
        hand_obj.curl_index(1, duration)
        hand_obj.curl_thumb(1, thumb_duration)

    def scissor(self, hand_obj):
        duration = self.scissor_duration_ms
        side_str = getattr(hand_obj, "side", "unknown")
        logger.info(f"Executing scissor on {side_str} hand (duration: {duration} ms)")
        hand_obj.curl_pinky(0, duration)
        hand_obj.curl_ring(0, duration)
        hand_obj.curl_thumb(0, duration)
        hand_obj.curl_middle(1, duration)
        hand_obj.curl_index(1, duration)

    def handle_command(self, command, hand_obj, mutex, side):
        command = command.strip().lower()
        logger.info(f"Received command '{command}' for {side} hand")

        if command not in self.commands_map:
            logger.warning(f"Unknown command '{command}' for {side} hand.")
            return

        if not mutex.acquire(blocking=False):
            active_cmd = self.right_active_command if side == "right" else self.left_active_command
            logger.warning(f"Ignored command '{command}' for {side} hand: Busy executing '{active_cmd}'.")
            return

        if side == "right":
            self.right_active_command = command
        else:
            self.left_active_command = command
        mutex.release()

        t = threading.Thread(
            target=self.execute_motion_thread,
            args=(command, hand_obj, mutex, side),
            daemon=True,
        )
        if side == "right":
            self.right_thread = t
        else:
            self.left_thread = t
        t.start()

    def execute_motion_thread(self, command, hand_obj, mutex, side):
        with mutex:
            logger.info(f"Starting execution of motion '{command}' on {side} hand")
            motion_func = self.commands_map[command]
            try:
                if hand_obj is not None:
                    motion_func(hand_obj)
                else:
                    logger.warning(f"Hand object for {side} is None (hamsa package not connected). Skipped physical call.")
                logger.info(f"Successfully completed motion '{command}' on {side} hand")

                if side == "right":
                    self.right_state = command
                else:
                    self.left_state = command
            except Exception as e:
                logger.error(f"Failed to execute motion '{command}' on {side} hand: {e}")
            finally:
                if side == "right":
                    self.right_active_command = None
                else:
                    self.left_active_command = None


def main():
    controller = HamsaMotionController()

    prev_buttons = {
        "button_a": False,
        "button_b": False,
        "button_x": False,
        "button_y": False,
    }

    node = dora.Node()
    logger.info("dora-openarm-hamsa node started and listening to button inputs...")

    for event in node:
        if event["type"] == "INPUT":
            event_id = event["id"]
            if event_id in prev_buttons:
                val_arr = event["value"]
                if len(val_arr) > 0:
                    curr_val = bool(val_arr[0].as_py()) if hasattr(val_arr[0], "as_py") else bool(val_arr[0])
                else:
                    curr_val = False
                was_pressed = prev_buttons[event_id]
                prev_buttons[event_id] = curr_val


                # Process on Rising Edge (button press event: False -> True)
                if curr_val and not was_pressed:
                    logger.info(f"Button press detected: '{event_id}'")
                    if event_id == "button_a":
                        # Right Grip <-> Right Release
                        target_cmd = "release" if controller.right_state == "grab" else "grab"
                        controller.handle_command(target_cmd, right, controller.right_mutex, "right")

                    elif event_id == "button_x":
                        # Left Grip <-> Left Release
                        target_cmd = "release" if controller.left_state == "grab" else "grab"
                        controller.handle_command(target_cmd, left, controller.left_mutex, "left")

                    elif event_id == "button_b":
                        # Right Scissor <-> Right Release
                        target_cmd = "release" if controller.right_state == "scissor" else "scissor"
                        controller.handle_command(target_cmd, right, controller.right_mutex, "right")

                    elif event_id == "button_y":
                        # Left Scissor <-> Left Release
                        target_cmd = "release" if controller.left_state == "scissor" else "scissor"
                        controller.handle_command(target_cmd, left, controller.left_mutex, "left")


if __name__ == "__main__":
    main()
