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

"""
Meta Quest UDP pose receiver — specification
==============================================

[1. Incoming JSON Structure]
- t:  headset monotonic timestamp (seconds, Time.realtimeSinceStartup)
- lc / rc / rf:  pose objects (left controller / right controller / reference)
    - x, y, z: Unity left-handed world coordinates (meters)
    - qx, qy, qz, qw: Unity left-handed rotation (Quaternion)
- lt / rt: left/right index trigger  0.0–1.0
- lg / rg: left/right grip           0.0–1.0
- lsx / lsy / rsx / rsy: thumbstick axes  -1.0–1.0
- a / b / x / y: buttons
- v:  overall validity   0=OK, 1=STALE, 2=INVALID
- vl: left controller validity
- vr: right controller validity

[2. Validity Handling]
- OK (0):     normal processing
- STALE (1):  HMD is sending last-good pose; pass through smoother normally
- INVALID(2): do not output pose; reset smoother so re-entry is jump-free
- buttons/triggers/grips are always forwarded regardless of pose validity

[3. Coordinate Transformation (LH to RH)]
1. Position Flip:
    p_mujoco = [x, y, -z]
2. Quaternion Flip:
    q_mujoco = [qw, -qx, -qy, qz]
3. Reference Rectification
   A saved reference pose (p_ref, R_ref) is subtracted so that the
   controller pose is expressed relative to where the operator was
   standing/looking when the reference was captured.  Two modes differ
   in which frame the relative pose is expressed in:

   NECK mode  — relative position is rotated into the HMD's frame:
     p_rel = R_ref_inv * (p_ctrl - p_ref)   (displacement in HMD axes)
     r_rel = R_ref_inv * r_ctrl             (orientation relative to HMD)

[4. Robot Workspace Mapping]
- p_out = R_FRAME * p_rel + FRAME_OFFSET_NECK
- r_out = R_FRAME * r_rel * R_FIX
    * R_FIX = Rot_z(90)
- Output poses are expressed in the scene's `arm_origin` site frame
  (chest-level origin between the arms), not in world coordinates.
  Downstream IK interprets targets in the same frame.
"""

import argparse
import time

import dora
import numpy as np
import pyarrow as pa
from scipy.spatial.transform import Rotation

from .smoothing import OneEuroPoseSmoother
from .udp_receiver import JsonUdpReceiver


def _map_trigger_to_gripper(trigger: float, side: str) -> float:
    """Map a trigger value (0.0–1.0) to a calibrated gripper angle in radians."""
    trigger = float(np.clip(trigger, 0.0, 1.0))
    if side == "right":
        open_deg, closed_deg = -45.0, 10.0
    elif side == "left":
        open_deg, closed_deg = 45.0, -10.0
    else:
        raise ValueError(f"Unsupported gripper side: {side!r}")
    return float(np.deg2rad(open_deg + trigger * (closed_deg - open_deg)))


# ── Frame alignment — edit here to tune ──────────────────────────────────────
_FRAME_ROT: np.ndarray = np.array(
    [
        [0.0, 0.0, -1.0],
        [-1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ],
    dtype=np.float64,
)

# Neutral hand position relative to the arm_origin site (chest level).
FRAME_OFFSET_NECK: np.ndarray = np.array([-0.085, 0, -0.14], dtype=np.float64)
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_HOST = "0.0.0.0"
_DEFAULT_PORT = 5006

VALID_OK = 0
VALID_STALE = 1
VALID_INVALID = 2
_VALID_NAMES = {VALID_OK: "OK", VALID_STALE: "STALE", VALID_INVALID: "INVALID"}

_R_FRAME = Rotation.from_matrix(_FRAME_ROT)
_IDENTITY_REF = {
    "x": 0.0,
    "y": 0.0,
    "z": 0.0,
    "qx": 0.0,
    "qy": 0.0,
    "qz": 0.0,
    "qw": 1.0,
}


def parse_lh_to_rh(c: dict) -> tuple[np.ndarray, Rotation]:
    """Convert a Unity left-handed pose dict to a right-handed (position, Rotation) pair.

    Input keys: x, y, z (meters), qx, qy, qz, qw (Unity quaternion, scalar-last).
    Flip: z → -z, qx → -qx, qy → -qy.
    """
    pos = np.array([c["x"], c["y"], -c["z"]], dtype=np.float64)
    rot = Rotation.from_quat([-c["qx"], -c["qy"], c["qz"], c["qw"]])
    return pos, rot


def pose_to_array(pos: np.ndarray, rot: Rotation) -> np.ndarray:
    q = rot.as_quat()
    return np.array([pos[0], pos[1], pos[2], q[3], q[0], q[1], q[2]], dtype=np.float32)


_POSE_STRUCT_TYPE = pa.struct({"pose": pa.list_(pa.float32())})


def build_pose_output(pose: np.ndarray) -> pa.Array:
    """Wrap a pose array as a length-1 StructArray: [{"pose": [...]}]."""
    return pa.array([{"pose": pose}], type=_POSE_STRUCT_TYPE)


class QuestPoseProcessor:
    def __init__(
        self, scale_x: float = 1.0, scale_y: float = 1.0, scale_z: float = 1.0
    ) -> None:
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.scale_z = scale_z

    def process(
        self, msg: dict
    ) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None]:
        ref_raw = msg.get("rf") # HMD 기준점 
        right_raw = msg.get("rc") # 왼손 컨트롤러
        left_raw = msg.get("lc") # 오른손 컨트롤러 

        # Unity 좌표계(왼손 좌표계) -> Mujoco, ROS2(오른손 좌표계) 변환
        # - p_ref : Ref(HMD)의 위치 벡터, r_ref : Ref(HMD)dml 회전 행렬
        p_ref, r_ref = parse_lh_to_rh(ref_raw or _IDENTITY_REF) 
        
        active_p_ref = p_ref # HMD 위치 값을 기준 위치 변수로 복사 할당
        active_r_ref_inv = r_ref.inv() # HMD 역회전 회전 객체

        # 손목 컨트롤러 방향과 로봇 그리퍼 축 방향을 정렬하기 위한 90도 회전 객체 생성 (z축 90도 오일러 각도)
        r_fix = Rotation.from_euler("z", 90, degrees=True)

        def _rectify(raw: dict) -> np.ndarray:
            """
            """
            p, r = parse_lh_to_rh(raw) # Unity 좌표계(왼손 좌표계) -> Mujoco, ROS2(오른손 좌표계) 변환
            p_rel = active_r_ref_inv.apply(p - active_p_ref) # HMD 원점 기준 컨트롤러의 3D 위치 차이 (상대 변위) 계산 후 HMD 회전각 만큼 역회전시켜 HMD 시선 방향 기준 상대 위치로 회전 변환
            r_rel = active_r_ref_inv * r # HMD 회전을 기준으로 한 컨트롤러의 상대 회전량 행렬 곱 게산
            
            p_out = _R_FRAME.apply(p_rel) + FRAME_OFFSET_NECK # 최종 로봇 기준 3D 목표 위치 획득

            # 어깨 폭 보정을 위한 가슴 중심 기준 X, Y, Z축 스케일링 적용 (Y축 기본 1.15 배로 벌림 감도 상승)
            p_out[0] = FRAME_OFFSET_NECK[0] + (p_out[0] - FRAME_OFFSET_NECK[0]) * self.scale_x
            p_out[1] = FRAME_OFFSET_NECK[1] + (p_out[1] - FRAME_OFFSET_NECK[1]) * self.scale_y
            p_out[2] = FRAME_OFFSET_NECK[2] + (p_out[2] - FRAME_OFFSET_NECK[2]) * self.scale_z

            r_out = _R_FRAME * r_rel * r_fix # 최종 로봇 기준 회전 객체 획득

            return pose_to_array(p_out, r_out)

        pose_right = _rectify(right_raw) if right_raw is not None else None
        pose_left = _rectify(left_raw) if left_raw is not None else None

        pose_reference = pose_to_array(p_ref, r_ref) if ref_raw is not None else None

        return pose_right, pose_left, pose_reference


def _run(args: argparse.Namespace) -> None:

    receiver = JsonUdpReceiver(
        args.host, args.port
    )
    processor = QuestPoseProcessor(
        scale_x=args.scale_x, scale_y=args.scale_y, scale_z=args.scale_z
    )

    smoother_right = OneEuroPoseSmoother(
        min_cutoff=2.0, beta=0.04, d_cutoff=1.5
    )
    smoother_left = OneEuroPoseSmoother(
        min_cutoff=2.0, beta=0.04, d_cutoff=1.5
    )
    smoother_reference = OneEuroPoseSmoother(
        min_cutoff=2.0, beta=0.04, d_cutoff=1.5
    )

    prev_v_right = VALID_OK
    prev_v_left = VALID_OK
    prev_v_overall = VALID_OK
    prev_v_reference = VALID_OK

    node = dora.Node()
    node.send_output("status", pa.array(["ready"]))

    for event in node:
        if event["type"] != "INPUT" or event["id"] != "tick":
            continue

        recv_ts = receiver.drain_recv_timestamps()

        if recv_ts:
            node.send_output("vr_receive_times", pa.array(recv_ts, type=pa.int64()))

        msg = receiver.latest()

        if msg is None:
            continue

        now = time.perf_counter()

        # 포즈 추적 유효성 검사 (VR 기기에서 보냄, VALID_STALE: 컨트롤러가 잠시 안 보여 마지막 정상 위치 유지 중, VALID_INVALID: 추적 완전 손실, VALID_OK: 카메라 추적 정상)
        v_overall = int(msg["v"]) if "v" in msg else VALID_OK # (전체)
        v_right = int(msg["vr"]) if "vr" in msg else VALID_OK # (오른손)
        v_left = int(msg["vl"]) if "vl" in msg else VALID_OK # (왼손)

        # 추적 상태 변경 시 로그 출력
        if v_overall != prev_v_overall: # 전체
            """
                추적 상태가 변화했을 떄만, 하단 로그를 출력
                [receiver] validity: OK → STALE (L=OK, R=STALE)
            """
            print(
                f"[receiver] validity: {_VALID_NAMES[prev_v_overall]} → {_VALID_NAMES[v_overall]} "
                f"(L={_VALID_NAMES[v_left]}, R={_VALID_NAMES[v_right]})"
            )
            prev_v_overall = v_overall

        # VR 기기로 부터 받은 데이터로 부터 변환된 로봇 좌표게 포즈 획득 (오른손, 왼손, HMD)
        pose_right_raw, pose_left_raw, pose_reference_raw = processor.process(msg)

        """
            컨트롤러가 카메라 밖으로 나갔다가 다시 들어오거나, 손에 가려졌다가 다시 나타날 때, 손 위치가 순간적으로 크게 점프(Jump)할 수 있음
            이때, 과거 위치 데이터를 기억하고 있던 필터(OneEuroFilter)가 작동하면, 로봇 팔이 이전 위치에서 새 위치로 확 튀거나 뒤 늦게 들어오는 현상이 발생함
            이를 방지하기 위해서, 추적이 끊기는 순간 필터의 과거 기록을 싹 지워버려, 추적 재기 시 로봇이 점프 없이 부드럽게 새 포즈부터 다시 시작하도록 만든 안전 장
        """

        if v_right == VALID_INVALID: # 오른손 추적 실패시
            if prev_v_right != VALID_INVALID: # 손실이 시작된 "첫 순간" 감지
                smoother_right.reset() # 스무더(필터) 히스토리 초기화
            pose_right = None # 잘못된 포즈 데이터는 None으로 해서 IK 등의 작업 수행 못하도록 원천 차단
        else: # 오른손 추적 정상 (OK 또는 STALE 시)
            pose_right = smoother_right.smooth(now, pose_right_raw)

        if v_left == VALID_INVALID: # 왼손 추적 실패시
            if prev_v_left != VALID_INVALID: # 손실이 시작된 "첫 순간" 감지 
                smoother_left.reset() # 스무더(필터) 히스토리 초기화
            pose_left = None # 잘못된 포즈 데이터는 None으로 해서 IK 등의 작업 수행 못하도록 원천 차단
        else: # 왼손 추적 정상 (OK 또는 STALE 시)
            pose_left = smoother_left.smooth(now, pose_left_raw)

        if v_overall == VALID_INVALID: # HMD 추적 실패시
            if prev_v_reference != VALID_INVALID: # 손실이 시작된 "첫 순간" 감지
                smoother_reference.reset() # 스무더(필터) 히스토리 초기화
            pose_reference = None # 잘못된 포즈 데이터는 None으로 해서 IK 등의 작업 수행 못하도록 원천 차단
        else: # HMD 추적 정상 (OK 또는 STALE 시)
            pose_reference = smoother_reference.smooth(now, pose_reference_raw)

        prev_v_right = v_right
        prev_v_left = v_left
        prev_v_reference = v_overall

        ts = {"timestamp": time.time_ns()}

        if pose_right is not None and ("rg" in msg or "rt" in msg):
            """
                pose_with_gripper (길이 8의 float32 np.ndarray):
                [x, y, z, qw, qx, qy, qz, gripper_angle]

                - Pose 기준 (x, y, z, qw, qx, qy, qz):
                  Unity 오른손 좌표계를 오른손 좌표계(MuJoCo)로 변환 후, 헤드셋(HMD) 리셋 위치 기준의 
                  상대 변화량을 로봇의 가슴 원점 프레임(`arm_origin` site) 및 기본 오프셋(`FRAME_OFFSET_NECK`)에 
                  투영한 최종 위치 및 회전 값.

                - Gripper Angle 기준 (gripper_angle):
                  VR 컨트롤러의 트리거 입력 값(rg/rt, 0.0~1.0)을 로봇 우측 그리퍼의 
                  열림/닫힘 보정 각도범위(-45° ~ 10°)로 선형 매핑하여 라디안(rad)으로 변환한 값.

                예시 데이터:
                np.array([-0.085, 0.20, -0.14, 1.0, 0.0, 0.0, 0.0, -0.785398], dtype=np.float32)
            """
            grip_val = float(msg.get("rg", msg.get("rt", 0.0)))
            gripper_angle = _map_trigger_to_gripper(grip_val, "right")
            pose_with_gripper = np.concatenate([pose_right, [gripper_angle]], axis=0)
            node.send_output("pose_right", build_pose_output(pose_with_gripper), ts)

        if pose_left is not None and ("lg" in msg or "lt" in msg):
            """
                pose_with_gripper (길이 8의 float32 np.ndarray):
                [x, y, z, qw, qx, qy, qz, gripper_angle]

                - Pose 기준 (x, y, z, qw, qx, qy, qz):
                  Unity 왼손 좌표계를 오른손 좌표계(MuJoCo)로 변환 후, 헤드셋(HMD) 리셋 위치 기준의 
                  상대 변화량을 로봇의 가슴 원점 프레임(`arm_origin` site) 및 기본 오프셋(`FRAME_OFFSET_NECK`)에 
                  투영한 최종 위치 및 회전 값.

                - Gripper Angle 기준 (gripper_angle):
                  VR 컨트롤러의 트리거 입력 값(lg/lt, 0.0~1.0)을 로봇 좌측 그리퍼의 
                  열림/닫힘 보정 각도범위(45° ~ -10°)로 선형 매핑하여 라디안(rad)으로 변환한 값.

                예시 데이터:
                np.array([-0.085, -0.20, -0.14, 1.0, 0.0, 0.0, 0.0, 0.785398], dtype=np.float32)
            """
            grip_val = float(msg.get("lg", msg.get("lt", 0.0)))
            gripper_angle = _map_trigger_to_gripper(grip_val, "left")
            pose_with_gripper = np.concatenate([pose_left, [gripper_angle]], axis=0)
            node.send_output("pose_left", build_pose_output(pose_with_gripper), ts) # 시간 동기화를 위해 ns 단위의 timestamp도 보냄 (혹은 지연 시간(Latency) 측정 및 모니터링, 그리고 AI 학습 데이터 수집을 위한 시계열 축으로도 사용 가능)

        if pose_reference is not None:
            node.send_output("pose_reference", build_pose_output(pose_reference), ts)

        if "rt" in msg:
            node.send_output(
                "trigger_right", pa.array([msg["rt"]], type=pa.float32()), ts
            )
        if "lt" in msg:
            node.send_output(
                "trigger_left", pa.array([msg["lt"]], type=pa.float32()), ts
            )
        if "rg" in msg:
            node.send_output(
                "grip_right", pa.array([float(msg["rg"])], type=pa.float32()), ts
            )
        if "lg" in msg:
            node.send_output(
                "grip_left", pa.array([float(msg["lg"])], type=pa.float32()), ts
            )
        if "lsx" in msg:
            node.send_output(
                "joystick_x_left",
                pa.array([float(msg["lsx"])], type=pa.float32()),
                ts,
            )
        if "lsy" in msg:
            node.send_output(
                "joystick_y_left",
                pa.array([float(msg["lsy"])], type=pa.float32()),
                ts,
            )
        if "rsx" in msg:
            node.send_output(
                "joystick_x_right",
                pa.array([float(msg["rsx"])], type=pa.float32()),
                ts,
            )
        if "rsy" in msg:
            node.send_output(
                "joystick_y_right",
                pa.array([float(msg["rsy"])], type=pa.float32()),
                ts,
            )
        if "a" in msg:
            node.send_output(
                "button_a", pa.array([bool(msg["a"])], type=pa.bool_()), ts
            )
        if "b" in msg:
            node.send_output(
                "button_b", pa.array([bool(msg["b"])], type=pa.bool_()), ts
            )
        if "x" in msg:
            node.send_output(
                "button_x", pa.array([bool(msg["x"])], type=pa.bool_()), ts
            )
        if "y" in msg:
            node.send_output(
                "button_y", pa.array([bool(msg["y"])], type=pa.bool_()), ts
            )

    receiver.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Meta Quest VR pose receiver (dora node)"
    )
    parser.add_argument("--host", default=_DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT)
    parser.add_argument(
        "--scale-x",
        type=float,
        default=1.0,
        help="Forward/backward movement scale multiplier",
    )
    parser.add_argument(
        "--scale-y",
        type=float,
        default=1.0,
        help="Left/right arm stretch scale multiplier (default: 1.0)",
    )
    parser.add_argument(
        "--scale-z",
        type=float,
        default=1.0,
        help="Up/down movement scale multiplier",
    )
    args = parser.parse_args()
    _run(args)


if __name__ == "__main__":
    main()
