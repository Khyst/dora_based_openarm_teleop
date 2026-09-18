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

import time

import dora
import argparse
import numpy as np
import pyarrow as pa

from scipy.spatial.transform import Rotation

from .smoothing import OneEuroPoseSmoother
from .udp_receiver import JsonUdpReceiver


def _discretize_trigger(val: float) -> float:
    """Discretize trigger input [0.0, 1.0] into 5 levels (0.0, 0.25, 0.5, 0.75, 1.0)."""
    return round(float(np.clip(val, 0.0, 1.0)) * 4.0) / 4.0


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
# FRAME_OFFSET_NECK: np.ndarray = np.array([-0.085, 0, -0.14], dtype=np.float64)
FRAME_OFFSET_NECK: np.ndarray = np.array([-0.085, 0, -0.05], dtype=np.float64)
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_HOST = "0.0.0.0" # Default Host IP for UDP server (listening on all available interfaces)
_DEFAULT_PORT = 5006 # Default UDP Port for receiving VR data

VALID_OK = 0 # VALID_OK: 컨트롤러가 카메라 추적 정상
VALID_STALE = 1 # VALID_STALE: 컨트롤러가 잠시 안 보여 마지막 정상 위치 유지 중
VALID_INVALID = 2 # VALID_INVALID: 추적 완전 손실
_VALID_NAMES = {VALID_OK: "OK", VALID_STALE: "STALE", VALID_INVALID: "INVALID"} # To match with the enum values used in the other Dora nodes

_R_FRAME = Rotation.from_matrix(_FRAME_ROT) # Rotation matrix for frame alignment (LH to RH conversion)
_POSE_STRUCT_TYPE = pa.struct({"pose": pa.list_(pa.float32())})

LOG_INTERVAL = 0.1  # 10Hz (0.1초 마다 출력)

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


def build_pose_output(pose: np.ndarray) -> pa.Array:
    """Wrap a pose array as a length-1 StructArray: [{"pose": [...]}]."""
    return pa.array([{"pose": pose}], type=_POSE_STRUCT_TYPE)


class VRStateLogger:
    """터미널에서 VR 포즈 및 입력 상태를 대시보드 형태로 가독성 있게 로깅하기 위한 헬퍼 클래스"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"

    @classmethod
    def format_pose(cls, pose_arr: np.ndarray | None) -> str:
        if pose_arr is None:
            return f"{cls.RED}None{cls.RESET}"
        pos = f"Pos({pose_arr[0]:6.3f}, {pose_arr[1]:6.3f}, {pose_arr[2]:6.3f})"
        rot = f"Quat({pose_arr[3]:5.2f}, {pose_arr[4]:5.2f}, {pose_arr[5]:5.2f}, {pose_arr[6]:5.2f})"
        grip = f" Grip({np.rad2deg(pose_arr[7]):5.1f}°)" if len(pose_arr) == 8 else ""
        return f"{cls.CYAN}{pos}{cls.RESET} | {cls.MAGENTA}{rot}{cls.RESET}{grip}"

    @classmethod
    def print_dashboard(
        cls,
        v_overall: int,
        v_left: int,
        v_right: int,
        pose_left: np.ndarray | None,
        pose_right: np.ndarray | None,
        msg: dict,
    ):
        def get_v_str(val):
            name = _VALID_NAMES.get(val, "UNKNOWN")
            if val == VALID_OK:
                return f"{cls.GREEN}{name}{cls.RESET}"
            elif val == VALID_STALE:
                return f"{cls.YELLOW}{name}{cls.RESET}"
            return f"{cls.RED}{name}{cls.RESET}"

        btn_a = f"{cls.GREEN}A{cls.RESET}" if msg.get("a") else "a"
        btn_b = f"{cls.GREEN}B{cls.RESET}" if msg.get("b") else "b"
        btn_x = f"{cls.GREEN}X{cls.RESET}" if msg.get("x") else "x"
        btn_y = f"{cls.GREEN}Y{cls.RESET}" if msg.get("y") else "y"

        lt, rt = msg.get("lt", 0.0), msg.get("rt", 0.0)
        lg, rg = msg.get("lg", 0.0), msg.get("rg", 0.0)
        lsx, lsy = msg.get("lsx", 0.0), msg.get("lsy", 0.0)
        rsx, rsy = msg.get("rsx", 0.0), msg.get("rsy", 0.0)

        print("\033[H\033[J", end="")  # 화면 덮어쓰기

        print(f"{cls.BOLD}=================== Quest Teleop Monitor ==================={cls.RESET}")
        print(f" Status    : Overall[{get_v_str(v_overall)}] | Left[{get_v_str(v_left)}] | Right[{get_v_str(v_right)}]")
        print(f"------------------------------------------------------------")
        print(f" {cls.BOLD}[LEFT ARM]{cls.RESET}")
        print(f"  - Pose   : {cls.format_pose(pose_left)}")
        print(f"  - Analog : Trigger={lt:.2f} | Grip={lg:.2f} | Stick=({lsx:+.2f}, {lsy:+.2f})")
        print(f"  - Button : [{btn_x}] [{btn_y}]")
        print(f"------------------------------------------------------------")
        print(f" {cls.BOLD}[RIGHT ARM]{cls.RESET}")
        print(f"  - Pose   : {cls.format_pose(pose_right)}")
        print(f"  - Analog : Trigger={rt:.2f} | Grip={rg:.2f} | Stick=({rsx:+.2f}, {rsy:+.2f})")
        print(f"  - Button : [{btn_a}] [{btn_b}]")
        print(f"================================================------------")


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
        right_raw = msg.get("rc") # 오른손 컨트롤러
        left_raw = msg.get("lc") # 왼손 컨트롤러 

        # Unity 좌표계(왼손 좌표계) -> Mujoco, ROS2(오른손 좌표계) 변환
        # p_ref : Ref(HMD)의 위치 벡터, r_ref : Ref(HMD)의 회전 행렬
        
        if ref_raw is None:
            """
                기준 점 값이 들어오지 않은 경우 차단하기
            """
            return None, None, None
        
        p_ref, r_ref = parse_lh_to_rh(ref_raw)
        active_p_ref = p_ref # HMD 위치 값을 기준 위치 변수로 복사 할당
        active_r_ref_inv = r_ref.inv() # HMD 역회전 회전 객체 (Why?: 역행렬은 HMD(헤드셋) 기준 컨트롤러의 상대 위치, 상대 회전량을 계산하기 위함)

        # 손목 컨트롤러 방향과 로봇 그리퍼 축 방향을 정렬하기 위한 90도 회전 객체 생성 (z축 90도 오일러 각도)
        r_fix = Rotation.from_euler("z", 90, degrees=True)

        def _rectify(raw: dict) -> np.ndarray:
            """
            """
            p, r = parse_lh_to_rh(raw) # Unity 좌표계(왼손 좌표계) -> Mujoco, ROS2(오른손 좌표계) 변환
            p_rel = active_r_ref_inv.apply(p - active_p_ref) # HMD 원점 기준 컨트롤러의 3D 위치 차이 (상대 변위) 계산 후 HMD 회전각 만큼 역회전시켜 HMD 시선 방향 기준 상대 위치로 회전 변환
            r_rel = active_r_ref_inv * r # HMD 회전을 기준으로 한 컨트롤러의 상대 회전량 행렬 곱 게산
            
            p_out = _R_FRAME.apply(p_rel) + FRAME_OFFSET_NECK # 최종 로봇 기준 3D 목표 위치 획득

            # 어깨 폭 보정을 위한 가슴 중심 기준 X, Y, Z축 스케일링 적용 (Y축 기본 N배로 벌림 감도 상승)
            p_out[0] = FRAME_OFFSET_NECK[0] + (p_out[0] - FRAME_OFFSET_NECK[0]) * self.scale_x
            p_out[1] = FRAME_OFFSET_NECK[1] + (p_out[1] - FRAME_OFFSET_NECK[1]) * self.scale_y
            p_out[2] = FRAME_OFFSET_NECK[2] + (p_out[2] - FRAME_OFFSET_NECK[2]) * self.scale_z

            r_out = _R_FRAME * r_rel * r_fix # 최종 로봇 기준 회전 객체 획득

            return pose_to_array(p_out, r_out)

        pose_right = _rectify(right_raw) if right_raw is not None else None
        pose_left = _rectify(left_raw) if left_raw is not None else None

        pose_reference = pose_to_array(p_ref, r_ref) if ref_raw is not None else None

        # 최종 반환되는 값은, 로봇의 가슴 중심 기준 Pose 값 
        return pose_right, pose_left, pose_reference


def _run(args: argparse.Namespace) -> None:

    receiver = JsonUdpReceiver(args.host, args.port)
    processor = QuestPoseProcessor(scale_x=args.scale_x, scale_y=args.scale_y, scale_z=args.scale_z)

    smoother_right = OneEuroPoseSmoother(min_cutoff=2.0, beta=0.04, d_cutoff=1.5)
    smoother_left = OneEuroPoseSmoother(min_cutoff=2.0, beta=0.04, d_cutoff=1.5)
    smoother_reference = OneEuroPoseSmoother(min_cutoff=2.0, beta=0.04, d_cutoff=1.5)

    prev_v_right = VALID_OK
    prev_v_left = VALID_OK
    prev_v_overall = VALID_OK
    prev_v_reference = VALID_OK
    last_log_time = 0.0 # 디버깅 정보 기록 시간 기록용 변수

    node = dora.Node()
    node.send_output("status", pa.array(["ready"]))

    for event in node:
        
        if event["type"] != "INPUT" or event["id"] != "tick":
            """
                매번 쏟아지는 모든 종류의 이벤트(Event) 중에서, 
                Dora의 'tick'이라는 이름의 'INPUT' 타입 이벤트만 "필터링"하여 아래 로직을 수행
            """
            continue

        recv_ts = receiver.drain_recv_timestamps()

        if recv_ts:
            node.send_output("vr_receive_times", pa.array(recv_ts, type=pa.int64())) # VR 기기에서 데이터를 수신한 실제 타임스탬프. 이를 통해 수신 지연 시간 등을 파악할 수 있음.

        msg = receiver.latest()

        if msg is None:
            continue

        now = time.perf_counter()

        # 포즈 추적 유효성 검사 
        v_overall = int(msg["v"]) if "v" in msg else VALID_OK # (전체)
        v_right = int(msg["vr"]) if "vr" in msg else VALID_OK # (오른손)
        v_left = int(msg["vl"]) if "vl" in msg else VALID_OK # (왼손)

        # 추적 상태 변경 시 로그 출력
        if v_overall != prev_v_overall: # 전체
            """
                추적 상태가 변화했을 떄만, 하단 로그를 출력
                예시: [receiver] validity: OK → STALE (L=OK, R=STALE)
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

        pose_right_with_hand = None
        if pose_right is not None and ("rg" in msg):            
            """
                dora node로 부터 쏟아지는 모든 메세지들은 (timestamp를 포함해서) send_output으로 내보내진다
                이 노드에서 내보내는 데이터: 
                - "pose_right : {"pose": {"x": 0.0, "y": 0.0, "z": 0.0, "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0}, "gripper": 0.0} (로봇 오른손 로봇 팔 기준 좌표계와 회전, + "gripper": 0.0~1.0)
                - "pose_left" : {"pose": {"x": 0.0, "y": 0.0, "z": 0.0, "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0}, "gripper": 0.0} (로봇 왼손 로봇 팔 기준 좌표계와 회전, + "gripper": 0.0~1.0)
                - "pose_reference" : {"pose": {"x": 0.0, "y": 0.0, "z": 0.0, "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0}} (로봇의 가슴 부근 좌표계와 회전)

                Pose 데이터 설명 :
                * 헤드셋(HMD) 리셋 위치 기준에 대하여 Unity 오른손 좌표계를 오른손 좌표계(MuJoCo)로 변환 후
                * 상대 변화량을 로봇의 가슴 원점 프레임(`arm_origin` site) 및 기본 오프셋(`FRAME_OFFSET_NECK`)에 투영한 최종 위치 및 회전 값.

                Gripper 데이터 설명
                * VR 컨트롤러의 트리거 입력 값(rg/rt, 0.0~1.0)을 로봇 우측 그리퍼의 
            """

            trigger_val = _discretize_trigger(msg.get("rt", 0.0))
            pose_right_with_hand = np.concatenate([pose_right, [trigger_val]], axis=0)
            node.send_output("pose_right", build_pose_output(pose_right_with_hand), ts)

        pose_left_with_hand = None
        if pose_left is not None and ("lg" in msg):
            """
                dora node로 부터 쏟아지는 모든 메세지들은 (timestamp를 포함해서) send_output으로 내보내진다
                이 노드에서 내보내는 데이터: 
                - "pose_right : {"pose": {"x": 0.0, "y": 0.0, "z": 0.0, "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0}, "gripper": 0.0} (로봇 오른손 로봇 팔 기준 좌표계와 회전, + "gripper": 0.0~1.0)
                - "pose_left" : {"pose": {"x": 0.0, "y": 0.0, "z": 0.0, "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0}, "gripper": 0.0} (로봇 왼손 로봇 팔 기준 좌표계와 회전, + "gripper": 0.0~1.0)
                - "pose_reference" : {"pose": {"x": 0.0, "y": 0.0, "z": 0.0, "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0}} (로봇의 가슴 부근 좌표계와 회전)

                Pose 데이터 설명 :
                * 헤드셋(HMD) 리셋 위치 기준에 대하여 Unity 오른손 좌표계를 오른손 좌표계(MuJoCo)로 변환 후
                * 상대 변화량을 로봇의 가슴 원점 프레임(`arm_origin` site) 및 기본 오프셋(`FRAME_OFFSET_NECK`)에 투영한 최종 위치 및 회전 값.

                Gripper 데이터 설명
                * VR 컨트롤러의 트리거 입력 값(rg/rt, 0.0~1.0)을 로봇 우측 그리퍼의 
            """
            trigger_val = _discretize_trigger(msg.get("lt", 0.0))
            pose_left_with_hand = np.concatenate([pose_left, [trigger_val]], axis=0)
            node.send_output("pose_left", build_pose_output(pose_left_with_hand), ts)

        if pose_reference is not None:
            node.send_output("pose_reference", build_pose_output(pose_reference), ts)

        # 트리거 토글 관련 (검지 손가락 부분), 트리거의 눌림 정도에 따라 핸드의 Curl 값으로 제어 매핑
        if "rt" in msg:
            rt_level = _discretize_trigger(msg["rt"])
            node.send_output(
                "trigger_right", pa.array([rt_level], type=pa.float32()), ts
            )
        if "lt" in msg:
            lt_level = _discretize_trigger(msg["lt"])
            node.send_output(
                "trigger_left", pa.array([lt_level], type=pa.float32()), ts
            )

        # 그리퍼 토글 관련 (중지 손가락 부분), VR Teleop 사용에 대한 트리거
        if "rg" in msg:
            node.send_output(
                "grip_right", pa.array([float(msg["rg"])], type=pa.float32()), ts
            )
        if "lg" in msg:
            node.send_output(
                "grip_left", pa.array([float(msg["lg"])], type=pa.float32()), ts
            )

        # 조이스틱 토글 관련 (엄지 손가락 부분)
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

        # 버튼 토글 관련 (가장 아랫단 4개의 버튼, 혹은 방향 버튼)
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

        # [Check quest driver received info] (--debug-value 플래그가 설정되어 있을 때만 모니터링 대시보드 출력)
        # 특정 주기로 트리거, 조이스틱, 버튼 입력 정보와 헤드셋/컨트롤러의 자세 정보를 터미널에 모니터링 
        if args.debug_value and (now - last_log_time >= LOG_INTERVAL):
            VRStateLogger.print_dashboard(
                v_overall=v_overall,
                v_left=v_left,
                v_right=v_right,
                pose_left=pose_left_with_hand if pose_left_with_hand is not None else pose_left,
                pose_right=pose_right_with_hand if pose_right_with_hand is not None else pose_right,
                msg=msg,
            )
            last_log_time = now

    receiver.close()


def main() -> None:
    """
        dora_openarm_vr의 메인 entrypoint
    """
    parser = argparse.ArgumentParser( description="Meta Quest VR pose receiver (dora node)" )

    parser.add_argument("--host", default=_DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT)
    parser.add_argument("--scale-x", type=float, default=1.0, help="Forward/backward movement scale multiplier",)
    parser.add_argument("--scale-y", type=float, default=1.0, help="Left/right arm stretch scale multiplier (default: 1.0)",)
    parser.add_argument("--scale-z", type=float, default=1.0, help="Up/down movement scale multiplier",)
    parser.add_argument("--debug-value", action="store_true", help="Enable terminal dashboard monitoring for Quest driver inputs and poses")
    args = parser.parse_args()

    _run(args)


if __name__ == "__main__":
    main()
