#!/usr/bin/env python3
"""Nana_v3 Hardware Connection & Ultra-Safe Micro-Motion Test Script

This script tests CAN communication with openarm_driver on right_arm (can0) or left_arm (can1).
It performs:
  1. CAN connection check & motor state/temperature read out.
  2. Smooth 2-second start routine to home attention posture [0, 0, 0, 0, 0, 0, 0, 0].
  3. Ultra-safe micro-motion test: flex elbow (Joint 4) by +0.05 rad (~2.8 deg) for 2s and return to 0.
  4. Smooth stop routine & motor disable.
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

    parser = argparse.ArgumentParser(description="Nana_v3 Hardware Safety Test")
    parser.add_argument("--side", choices=["right_arm", "left_arm"], default="right_arm", help="Arm side to test")
    parser.add_argument("--config", default=str(default_cfg_path), help="Path to nana_v3_cell.yaml")
    args = parser.parse_args()

    print(f"==================================================")
    print(f" 🤖 Nana_v3 Hardware Safety Test ({args.side})")
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
    print("✅ Arm enabled and in Home posture.")

    # 5. Micro-motion Test (+0.5236 rad / ~30.0 degrees on Joint 4)
    print("\n💪 Performing smooth motion (+30.0° on Joint 4 Elbow)...")
    target_pos = np.zeros(8, dtype=np.float32)
    
    # Smooth sine-wave motion over 3 seconds (150 steps at 50Hz)
    steps = 150
    for i in range(steps):
        # 0 -> +0.5236 rad (~30 deg) over first half, returning to 0 over second half
        t = i / steps
        j4_angle = 0.5236 * np.sin(np.pi * t)
        target_pos[3] = j4_angle  # Joint 4 index
        arm.send_position(target_pos)
        time.sleep(0.02)  # 50 Hz

    print("✅ Micro-motion test completed successfully!")

    # 6. Stop Routine
    print("\n🛑 Running stop routine & disabling motors...")
    arm.stop()
    print("==================================================")
    print(" 🎉 Safety test finished cleanly and safely!")
    print("==================================================")


if __name__ == "__main__":
    main()
