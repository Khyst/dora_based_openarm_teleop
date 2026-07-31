#!/usr/bin/env python3
"""Nana_v3 Hardware Connection & Registration Pose (A-Pose) Holding Script

This script tests CAN communication with openarm_driver on right_arm or left_arm
and moves the arm smoothly into an Alignment/Registration Pose:
  - Joint 1 (Shoulder): -30 deg (Left Arm) or +30 deg (Right Arm)
  - Joint 4 (Elbow): +30 deg (Both Arms)
"""

import argparse
import sys
import time
import numpy as np
from pathlib import Path

try:
    from openarm_driver import Config, SingleArmDriver
except ImportError as e:
    print(f"Error: openarm_driver is not installed in the python environment: {e}")
    sys.exit(1)


def main():
    script_dir = Path(__file__).resolve().parent
    default_cfg_path = script_dir / "openarm_driver" / "src" / "openarm_driver" / "configs" / "nana_v3_cell.yaml"

    parser = argparse.ArgumentParser(description="Nana_v3 Registration Pose Script")
    parser.add_argument("--side", choices=["right_arm", "left_arm"], default="right_arm", help="Arm side to test")
    parser.add_argument("--config", default=str(default_cfg_path), help="Path to nana_v3_cell.yaml")
    parser.add_argument("--hold_time", type=float, default=10.0, help="Time in seconds to hold the registration pose")
    args = parser.parse_args()

    print(f"==================================================")
    print(f" 🤖 Nana_v3 Alignment Pose Setup ({args.side})")
    print(f" Config: {args.config}")
    print(f"==================================================")

    # 1. Load Config
    try:
        cfg = Config(args.config)
        print("✅ Config loaded successfully.")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)

    # 2. Initialize Driver
    print(f"🔌 Connecting to {args.side} via CAN interface '{cfg.get_can_interface(args.side)}'...")
    try:
        arm = SingleArmDriver(arm_side=args.side, config=cfg)
        print("✅ SingleArmDriver initialized.")
    except Exception as e:
        print(f"❌ Failed to initialize driver (Make sure CAN interface is UP!): {e}")
        sys.exit(1)

    # 3. Read Initial State
    state = arm.fetch_state(refresh=True)
    print("\n--- 📊 Initial Motor State ---")
    print("Joint Positions (rad):", np.round(state["qpos"], 4))
    print("Joint Velocities:     ", np.round(state["qvel"], 4))
    print("MOS Temperatures (°C):", state["tmos"])

    # 4. Start Routine
    print("\n🚀 Enabling arm motors & running start routine (2-second soft home move)...")
    arm.start()
    print("✅ Arm enabled and in Home posture [0, ...].")

    # 5. Determine Registration Targets
    # Joint 1: Left arm is -30 deg (-0.5236 rad), Right arm is +30 deg (+0.5236 rad)
    # Joint 4: Both arms are +30 deg (+0.5236 rad)
    j1_target = -0.5236 if args.side == "left_arm" else 0.5236
    j4_target = 0.5236

    print(f"\n🎯 Target Alignment Angles ({args.side}):")
    print(f" - Joint 1 (Shoulder): {np.rad2deg(j1_target):+.1f}° ({j1_target:+.4f} rad)")
    print(f" - Joint 4 (Elbow)   : {np.rad2deg(j4_target):+.1f}° ({j4_target:+.4f} rad)")

    # 6. Smooth Motion to Alignment Pose (Cosine Interpolation over 3.0 seconds)
    print("\n💪 Moving smoothly to Alignment Pose (3.0 seconds)...")
    steps = 150  # 3 seconds at 50 Hz
    dt = 0.02
    
    target_pos = np.zeros(8, dtype=np.float32)

    for i in range(1, steps + 1):
        # Smooth minimum-jerk style step (0.0 -> 1.0)
        s = 0.5 * (1.0 - np.cos(np.pi * (i / steps)))
        
        target_pos[0] = j1_target * s  # Joint 1
        target_pos[3] = j4_target * s  # Joint 4
        
        arm.send_position(target_pos)
        time.sleep(dt)

    print("✅ Successfully reached Alignment Pose!")

    # 7. Hold Posture for Registration / Scan
    hold_sec = args.hold_time
    print(f"\n🧘 Holding Alignment Pose for {hold_sec} seconds (Press Ctrl+C to exit early)...")
    try:
        start_hold = time.time()
        while time.time() - start_hold < hold_sec:
            arm.send_position(target_pos)  # Keep publishing target position to maintain torque
            time.sleep(dt)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user during pose holding.")

    # 8. Return smoothly back to Home Pose [0, ...]
    print("\n↩️ Returning smoothly back to Home Pose (3.0 seconds)...")
    for i in range(1, steps + 1):
        s = 0.5 * (1.0 - np.cos(np.pi * (i / steps)))
        
        # Interpolate from target back to 0
        target_pos[0] = j1_target * (1.0 - s)
        target_pos[3] = j4_target * (1.0 - s)
        
        arm.send_position(target_pos)
        time.sleep(dt)

    # 9. Stop Routine
    print("\n🛑 Running stop routine & disabling motors...")
    arm.stop()
    print("==================================================")
    print(" 🎉 Alignment pose sequence finished cleanly!")
    print("==================================================")


if __name__ == "__main__":
    main()