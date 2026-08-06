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

from openarm_nana_kinematics import (
    Kinematics,
    register_common_args,
    register_ik_args,
    ik_params_from_args,
    setup_from_args,
)

_QPOS_STRUCT_TYPE = pa.struct({"qpos": pa.list_(pa.float32())})


def build_qpos_output(qpos: np.ndarray) -> pa.Array:
    """Wrap joint angles as a length-1 StructArray: [{"qpos": [...]}]."""
    return pa.array([{"qpos": qpos}], type=_QPOS_STRUCT_TYPE) # dora-rs 통신을 위해 pa.array 사용, 그 안에는 구조체(struct), 그 안에는 qpos라는 key와 qpos 배열을 넣음.

def extract_values(value: pa.Array, key: str) -> np.ndarray:
    """Read `key` from a length-1 StructArray, or a flat array as-is."""
    # 입력받은 value의 타입이 구조체(struct)인지 확인
    if pa.types.is_struct(value.type):
        # 구조체라면 해당 키의 값을 추출
        value = value.field(key)[0].values
    # numpy 배열로 변환
    return np.array(value, dtype=np.float32)

def _run(args: argparse.Namespace) -> None:

    # 인자들을 바탕으로 setup과 ik_params를 설정하고,
    # 이를 바탕으로 Kinematics 인스턴스를 생성
    kin = Kinematics(setup_from_args(args), ik_params_from_args(args))

    # Dora 노드를 생성
    node = dora.Node()
    node.send_output("status", pa.array(["ready"]))

    grip_right = 1.0  # Default to 1.0 if not connected
    grip_left = 1.0   # Default to 1.0 if not connected

    has_grip_right = False
    has_grip_left = False

    current_qpos_16 = np.zeros(16, dtype=np.float32)

    has_pos_right = False
    has_pos_left = False
    
    # Dora 이벤트 루프
    for event in node:
        
        # INPUT이 아닌 이벤트는 무시
        if event["type"] != "INPUT":
            continue

        eid = event["id"]

        if eid == "position_right":
            values = extract_values(event["value"], "qpos")
            if values.shape == (8,):
                current_qpos_16[:8] = values
                has_pos_right = True

                # 양쪽 피드백이 다 모였거나 갱신되면 동기화
                if has_pos_left or "left" not in kin.setup.sides:
                    kin.sync(current_qpos_16)
            continue

        elif eid == "position_left":
            values = extract_values(event["value"], "qpos")
            if values.shape == (8,):
                current_qpos_16[8:16] = values
                has_pos_left = True

                # 양쪽 피드백이 다 모였거나 갱신되면 동기화
                if has_pos_right or "right" not in kin.setup.sides:
                    kin.sync(current_qpos_16)
            continue

        # 기존 16차원 단일 position 처리 (유지)
        elif eid == "position":
            values = extract_values(event["value"], "qpos")
            if values.shape == (16,):
                kin.sync(values)
            continue


        # 팔꿈치 타겟 값 처리 (elbow_right / elbow_left)
        if eid == "elbow_right" and "right" in kin.setup.sides:
            values = extract_values(event["value"], "pose")
            if values.size in (3, 7, 8):
                elbow_pos = values[:3]
                kin.set_elbow_target("right", elbow_pos)
            continue

        elif eid == "elbow_left" and "left" in kin.setup.sides:
            values = extract_values(event["value"], "pose")
            if values.size in (3, 7, 8):
                elbow_pos = values[:3]
                kin.set_elbow_target("left", elbow_pos)
            continue

        # 그립 값을 받아오는 처리
        if eid == "grip_right":
            val = event["value"]
            grip_right = float(val[0].as_py() if hasattr(val, "as_py") else val[0])
            has_grip_right = True
            continue

        # 그립 값을 받아오는 처리
        elif eid == "grip_left":
            val = event["value"]
            grip_left = float(val[0].as_py() if hasattr(val, "as_py") else val[0])
            has_grip_left = True
            continue

        # 타겟 값을 받아오는 처리
        if eid == "target_right" and "right" in kin.setup.sides:
            # 그립 버튼이 눌려있지 않으면 타겟 업데이트를 건너뜀
            if has_grip_right and grip_right <= 0.5:
                continue  

            # 타겟 값을 받아오는 처리
            values = extract_values(event["value"], "pose")

            # 타겟 값의 형태가 올바르지 않으면 건너뜀
            if values.shape != (8,):
                print(
                    f"Warning: expected target_right[8], got {values.shape}. Skipping."
                )
                continue

            # 타겟 값에서 포즈와 그립 값을 추출
            pose = values[:7]
            gripper_angle = values[7]

            kin.set_target("right", pose) # IK 엔진에 타겟 값을 전달 (x,y,z,qw,qx,qy,qz)
            kin.set_gripper("right", gripper_angle) # 그립 값을 IK 엔진에 전달

        elif eid == "target_left" and "left" in kin.setup.sides:
            # 그립 버튼이 눌려있지 않으면 타겟 업데이트를 건너뜀
            if has_grip_left and grip_left <= 0.5:
                continue  

            # 타겟 값을 받아오는 처리
            values = extract_values(event["value"], "pose")

            # 타겟 값의 형태가 올바르지 않으면 건너뜀
            if values.shape != (8,):
                print(
                    f"Warning: expected target_left[8], got {values.shape}. Skipping."
                )
                continue

            # 타겟 값에서 포즈와 그립 값을 추출
            pose = values[:7]
            gripper_angle = values[7]

            kin.set_target("left", pose) # IK 엔진에 타겟 값을 전달 (x,y,z,qw,qx,qy,qz)
            kin.set_gripper("left", gripper_angle) # 그립 값을 IK 엔진에 전달

        else:
            continue

        # IK 엔진이 준비되었는지 확인
        if not kin.ready():
            continue

        result = kin.solve() # IK 엔진이 타겟 위치를 만족하는 joint 각도를 계산 

        # IK 계산이 실패하면 건너뜀
        if result is None:
            continue

        ts = {"timestamp": time.time_ns()} # 타임스탬프 생성
        node.send_output("position_right", build_qpos_output(result[:8]), ts) # 계산된 joint 각도를 output으로 전달
        node.send_output("position_left", build_qpos_output(result[8:16]), ts) # 계산된 joint 각도를 output으로 전달


def main() -> None:
    """Inverse kinematics for OpenArm."""
    parser = argparse.ArgumentParser( # 파이썬 CLI 파싱의 표준적인 패턴을 따르면서, 
        description="Mink IK dora node – OpenArm end-effector pose → joint angles"
    )

    # 외부 라이브러리(openarm_nana_kinematics)에 정의된 옵션 등록 함수들을 활용해, "노드 실행 파라미터"들을 체계적으로 수집하는 구조로 되어 있음
    register_common_args(parser) 
    register_ik_args(parser)

    # 사용자가 터미널에서 입력한 커맨드 라인 인자들(예: --control-method, --ik-weights 등)을 해석해서 args 객체에 담음
    args = parser.parse_args()

    # 수집된 파라미터들을 기반으로 실제 로직을 실행
    _run(args)


if __name__ == "__main__":
    main()
