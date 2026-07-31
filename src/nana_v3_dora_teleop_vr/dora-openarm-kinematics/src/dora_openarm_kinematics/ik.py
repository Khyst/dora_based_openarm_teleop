# Copyright 2026 Enactic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Dora node: mink-based differential IK solver for OpenArm.

Accepts end-effector pose targets and solves joint angles via mink's QP-based
differential IK. Both arms share one mink.Configuration and one QP solve per
step.

Pose convention:  float32[8] = [px, py, pz, qw, qx, qy, qz, gripper_angle]
Inputs:
  target_right – [{"pose": float32[8]}]  right EE target pose + gripper angle
  target_left  – [{"pose": float32[8]}]  left  EE target pose + gripper angle
  position     – [{"qpos": float32[16]}] current joint state right[8]+left[8]
                 (optional sync)
  Flat float32 arrays are also accepted for all inputs.

Outputs:
  position_right – [{"qpos": float32[8]}] solved right arm joint angles
  position_left  – [{"qpos": float32[8]}] solved left arm joint angles
  status         – ["ready"] on startup
"""

from __future__ import annotations

import argparse
import time

import dora
import numpy as np
import pyarrow as pa

from openarm_control import (
    Kinematics,
    register_common_args,
    register_ik_args,
    ik_params_from_args,
    setup_from_args,
)


_QPOS_STRUCT_TYPE = pa.struct({"qpos": pa.list_(pa.float32())})


def build_qpos_output(qpos: np.ndarray) -> pa.Array:
    """Wrap joint angles as a length-1 StructArray: [{"qpos": [...]}]."""
    return pa.array([{"qpos": qpos}], type=_QPOS_STRUCT_TYPE)


def extract_values(value: pa.Array, key: str) -> np.ndarray:
    """Read `key` from a length-1 StructArray, or a flat array as-is."""
    if pa.types.is_struct(value.type):
        value = value.field(key)[0].values
    return np.array(value, dtype=np.float32)


def _ramp_pose(
    current_pose: np.ndarray, target_pose: np.ndarray, max_step: float = 0.006
) -> np.ndarray:
    """Ramp 7D pose [x, y, z, qw, qx, qy, qz] gradually so that position delta per tick never exceeds max_step."""
    curr_p = current_pose[:3]
    targ_p = target_pose[:3]
    diff = targ_p - curr_p
    dist = float(np.linalg.norm(diff))

    if dist <= max_step or dist < 1e-6:
        return target_pose.copy()

    # Step position smoothly by max_step (0.6 cm / 0.02s => max 0.3 m/s)
    step_p = curr_p + (diff / dist) * max_step

    # Spherical linear interpolation (Slerp) for rotation
    try:
        r_curr = Rotation.from_quat(current_pose[3:])
        r_targ = Rotation.from_quat(target_pose[3:])
        slerp = Slerp([0.0, 1.0], Rotation.concatenate([r_curr, r_targ]))
        alpha = min(1.0, max_step / dist)
        r_next = slerp(alpha)
        next_quat = r_next.as_quat()
    except Exception:
        next_quat = target_pose[3:]

    return np.concatenate([step_p, next_quat], axis=0)


def _run(args: argparse.Namespace) -> None:
    kin = Kinematics(setup_from_args(args), ik_params_from_args(args))

    node = dora.Node()
    node.send_output("status", pa.array(["ready"]))

    grip_right = 1.0  # Default to 1.0 if not connected
    grip_left = 1.0   # Default to 1.0 if not connected
    has_grip_right = False
    has_grip_left = False

    # ── Safety Drop & Re-entry Smooth Ramping Guard ─────────────────────────
    # Max allowed 3D target jump distance when updating IK target (8 cm threshold)
    JUMP_THRESHOLD_METERS = 0.08
    # Max allowed step distance per tick (6 mm / 0.02s => max 0.3 m/s for smooth re-entry)
    MAX_STEP_METERS_PER_TICK = 0.006

    last_target_pose: dict[str, np.ndarray | None] = {"right": None, "left": None}
    engage_blocked: dict[str, bool] = {"right": False, "left": False}
    # ─────────────────────────────────────────────────────────────────────────

    for event in node:
        if event["type"] != "INPUT":
            continue

        eid = event["id"]

        if eid == "grip_right":
            val = event["value"]
            grip_right = float(val[0].as_py() if hasattr(val, "as_py") else val[0])
            has_grip_right = True
            continue
        elif eid == "grip_left":
            val = event["value"]
            grip_left = float(val[0].as_py() if hasattr(val, "as_py") else val[0])
            has_grip_left = True
            continue

        if eid == "position":
            values = extract_values(event["value"], "qpos")
            if values.shape == (16,):
                kin.sync(values)
            continue

        if eid == "target_right" and "right" in kin.setup.sides:
            if has_grip_right and grip_right <= 0.5:
                continue  # Skip IK target update when Grip handle is released!
            values = extract_values(event["value"], "pose")
            if values.shape != (8,):
                print(
                    f"Warning: expected target_right[8], got {values.shape}. Skipping."
                )
                continue
            pose = values[:7]
            gripper_angle = values[7]

            # Check 3D distance jump safety guard
            if last_target_pose["right"] is not None:
                dist = float(np.linalg.norm(pose[:3] - last_target_pose["right"][:3]))
                if dist > JUMP_THRESHOLD_METERS:
                    if not engage_blocked["right"]:
                        print(
                            f"[IK Safety Guard] RIGHT arm target jump detected ({dist*100:.1f} cm > {JUMP_THRESHOLD_METERS*100:.1f} cm). "
                            f"Holding robot pose. Move VR hand closer to resume."
                        )
                        engage_blocked["right"] = True
                    continue  # Drop update until VR hand is brought back within safety threshold
                elif engage_blocked["right"]:
                    print(
                        f"[IK Safety Guard] RIGHT arm re-entered safety zone ({dist*100:.1f} cm <= {JUMP_THRESHOLD_METERS*100:.1f} cm). Smoothly ramping IK."
                    )
                    engage_blocked["right"] = False

                # Smooth ramping for re-entry and step limiting
                next_pose = _ramp_pose(last_target_pose["right"], pose, max_step=MAX_STEP_METERS_PER_TICK)
            else:
                next_pose = pose

            last_target_pose["right"] = next_pose
            kin.set_target("right", next_pose)
            kin.set_gripper("right", gripper_angle)

        elif eid == "target_left" and "left" in kin.setup.sides:
            if has_grip_left and grip_left <= 0.5:
                continue  # Skip IK target update when Grip handle is released!
            values = extract_values(event["value"], "pose")
            if values.shape != (8,):
                print(
                    f"Warning: expected target_left[8], got {values.shape}. Skipping."
                )
                continue
            pose = values[:7]
            gripper_angle = values[7]

            # Check 3D distance jump safety guard
            if last_target_pose["left"] is not None:
                dist = float(np.linalg.norm(pose[:3] - last_target_pose["left"][:3]))
                if dist > JUMP_THRESHOLD_METERS:
                    if not engage_blocked["left"]:
                        print(
                            f"[IK Safety Guard] LEFT arm target jump detected ({dist*100:.1f} cm > {JUMP_THRESHOLD_METERS*100:.1f} cm). "
                            f"Holding robot pose. Move VR hand closer to resume."
                        )
                        engage_blocked["left"] = True
                    continue  # Drop update until VR hand is brought back within safety threshold
                elif engage_blocked["left"]:
                    print(
                        f"[IK Safety Guard] LEFT arm re-entered safety zone ({dist*100:.1f} cm <= {JUMP_THRESHOLD_METERS*100:.1f} cm). Smoothly ramping IK."
                    )
                    engage_blocked["left"] = False

                # Smooth ramping for re-entry and step limiting
                next_pose = _ramp_pose(last_target_pose["left"], pose, max_step=MAX_STEP_METERS_PER_TICK)
            else:
                next_pose = pose

            last_target_pose["left"] = next_pose
            kin.set_target("left", next_pose)
            kin.set_gripper("left", gripper_angle)

        else:
            continue

        if not kin.ready():
            continue

        result = kin.solve()
        if result is None:
            continue

        ts = {"timestamp": time.time_ns()}
        node.send_output("position_right", build_qpos_output(result[:8]), ts)
        node.send_output("position_left", build_qpos_output(result[8:16]), ts)


def main() -> None:
    """Inverse kinematics for OpenArm."""
    parser = argparse.ArgumentParser(
        description="Mink IK dora node – OpenArm end-effector pose → joint angles"
    )
    register_common_args(parser)
    register_ik_args(parser)
    args = parser.parse_args()
    _run(args)


if __name__ == "__main__":
    main()
