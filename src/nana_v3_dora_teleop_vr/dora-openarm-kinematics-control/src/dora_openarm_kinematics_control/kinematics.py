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

"""High-level FK + IK interface for OpenArm.

Poses are float32[7] = [px, py, pz, qw, qx, qy, qz], expressed in the
setup's origin frame (default: the scene's 'arm_origin' site; pass
--origin-frame world for world coordinates). FK returns poses in that
frame and IK targets are interpreted in it.

Usage:
    # FK only
    kin = Kinematics(setup)
    pose = kin.fk("right", joints)          # float32[7]
    pose_r, pose_l = kin.fk_bimanual(r, l)  # single mj_forward

    # FK + IK
    kin = Kinematics(setup, IKParams(dt=0.1, max_iters=5))
    kin.set_target("right", pose)
    kin.set_target("left", pose)
    result = kin.solve()                    # float32[16] or None
"""

from __future__ import annotations

import argparse
import pathlib
from dataclasses import dataclass

import mink
import mink.exceptions
import mujoco
import numpy as np
import yaml

from .config import (
    ARM_JOINT_VELOCITY_LIMITS_RAD_S,
    ArmSetup,
    frame_name,
)
from .poses import pose_to_se3


@dataclass
class IKParams:
    """Configuration for the mink QP-based IK solver."""

    position_cost: float = 1.0
    orientation_cost: float = 1.0
    lm_damping: float = 0.01
    damping: float = 0.25
    solver: str = "daqp"
    posture_cost: float = 0.01
    reach_posture_cost: float = 0.001
    reach_threshold: float = 0.35
    diag_reg: float = 0.0
    dt: float = 0.1
    max_iters: int = 5
    velocity_limits: dict[str, float] | None = None


class Kinematics:
    """Unified FK + IK for OpenArm, backed by MuJoCo + mink.

    FK is always available. IK is enabled by passing ``IKParams``.
    Both share the same ``ArmSetup`` context (model, resolver, frame IDs).
    """

    def __init__(self, setup: ArmSetup, ik_params: IKParams | None = None) -> None:
        """Initialize."""
        self.setup = setup
        self._ik: _IKSolver | None = (
            _IKSolver(setup, ik_params) if ik_params is not None else None
        )

    # ── FK ───────────────────────────────────────────────────────────────────

    def fk(self, side: str, joints: np.ndarray) -> np.ndarray:
        """Set qpos for one arm, run mj_forward, return float32[7] EE pose."""
        self.setup.joint_resolver.set_qpos(self.setup.data.qpos, joints, side)
        mujoco.mj_forward(self.setup.model, self.setup.data)
        return self.setup.read_ee_pose(side)

    def fk_bimanual(
        self, right: np.ndarray, left: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Set both arms and run a single mj_forward. Returns (pose_right, pose_left)."""
        self.setup.joint_resolver.set_qpos(self.setup.data.qpos, right, "right")
        self.setup.joint_resolver.set_qpos(self.setup.data.qpos, left, "left")
        mujoco.mj_forward(self.setup.model, self.setup.data)
        return self.setup.read_ee_pose("right"), self.setup.read_ee_pose("left")

    # ── IK ───────────────────────────────────────────────────────────────────

    def set_target(self, side: str, pose: np.ndarray) -> None:
        """Set EE target for one arm, in the origin frame.

        pose: float32[7] = [px, py, pz, qw, qx, qy, qz].
        """
        self._require_ik().set_target(side, pose)

    def set_gripper(self, side: str, value: float) -> None:
        """Pass through a gripper value; IK does not solve for it."""
        idx = 0 if side == "right" else 1
        self._require_ik()._gripper[idx] = value

    def sync(self, values16: np.ndarray) -> None:
        """Sync IK internal config from float32[16] driver state (right[8]+left[8])."""
        self._require_ik().sync(values16)

    def ready(self) -> bool:
        """Return True once all active arms have received at least one target this cycle."""
        return self._require_ik().ready()

    def solve(self) -> np.ndarray | None:
        """Run IK. Returns float32[16] (right[8]+left[8]) or None on failure."""
        return self._require_ik().solve()

    def _require_ik(self) -> _IKSolver:
        if self._ik is None:
            raise RuntimeError("Kinematics was not initialized with IKParams.")
        return self._ik


# ── internal IK implementation ────────────────────────────────────────────────


class _IKSolver:
    """
        MuJoCo의 물리 엔진과 Mink 라이브러리를 연동하여 IK를 해결하는 내부 클래스.
        이를 통해 로봇의 End-Effector(손목)를 원하는 6D(위치+방향) 좌표로 이동시킨다.
        
        [주요 기능]
        1. Pose Tracking (위치/방향 추적): 사용자가 설정한 목표 지오메트리를 로봇 손이 따라가도록 함.
        2. Posture Control (기본 자세 유지): 팔을 뻗는 도중 다른 관절(허리, 다리 등)이 튀는 현상을 방지.
        3. Velocity Control (속도 제어): 목표치로 바로 점프하지 않고, 부드러운 속도로 접근하도록 제어.
        4. Velocity Limits (속도 제한): 로봇의 물리적 한계를 넘어서는 움직임을 방지하여 안전한 제어를 보장.

        [구현 방법]
        이 클래스는 **Differential IK(차분 역기구학)** 방식을 사용합니다.
        
        **작동 원리:**
        1. 목표 자세(Target Pose)를 설정합니다.
        2. 현재 로봇 자세(Current Pose)와 목표 자세의 차이(Error)를 계산합니다.
        3. Mink 라이브러리의 최적화 솔버(QP Solver)를 사용하여 이 오차를 최소화하는 **속도(Velocity)**를 계산합니다.
        4. 계산된 속도를 현재 자세에 더해(Integrate) 다음 스텝의 자세를 업데이트합니다.
        5. 이 과정을 반복하여 로봇을 목표 자세로 수렴시킵니다.

    """

    def __init__(self, setup: ArmSetup, params: IKParams) -> None:
        
        # 1.1. 기본 제어 및 솔버 파라미터
        self._sides = setup.sides
        self._solver_name = params.solver
        self._joint_resolver = setup.joint_resolver
        self._dt = params.dt
        self._max_iters = params.max_iters
        
        # 1.2. Posture Task 관련 파라미터
        self._posture_cost = params.posture_cost
        self._reach_posture_cost = params.reach_posture_cost
        self._reach_threshold = params.reach_threshold
        
        # 1.3. 
        self._latest_targets: dict[str, np.ndarray] = {}

        # 1.4. Configuration 및 기본 자세(Null-space target) 초기화
        self._config = mink.Configuration(setup.model)
        self._config.update(q=setup.data.qpos.copy())
        mid_qpos = self._config.data.qpos.copy() # Null-space 제어 시 돌아가고 싶어 하는 기본 자세(Target Posture) 사용

        # =====================================================================
        # 2. Soft Objectives (약한 제약: 오차 최소화 목표)
        # =====================================================================
        task_kwargs = dict(
            position_cost=params.position_cost,
            orientation_cost=params.orientation_cost,
            lm_damping=params.lm_damping,
        )

        # 2.1. End-Effector Task (Relative 또는 Absolute)
        self._tasks: dict[str, mink.FrameTask | mink.RelativeFrameTask]

        if setup.origin_id is not None:
            self._tasks = {
                side: mink.RelativeFrameTask(
                    # Local 좌표계 제어
                    frame_name=_frame_name(setup, side),
                    frame_type=setup.frame_types[side],

                    root_name=frame_name(setup.model, setup.origin_id, setup.origin_type),
                    root_type=setup.origin_type,

                    **task_kwargs,
                )
                for side in setup.sides
            }
        else:
            self._tasks = {
                side: mink.FrameTask(
                    # Absolute World 좌표계 제어
                    frame_name=_frame_name(setup, side),
                    frame_type=setup.frame_types[side],

                    **task_kwargs,
                )
                for side in setup.sides
            }


        # 2.2. Null-space Posture Task (팔굽힘 자세 유지하도록 하는 Soft Objective Task)
        self._posture_task = mink.PostureTask(setup.model, cost=params.posture_cost)
        self._posture_task.set_target(mid_qpos)

        # =====================================================================
        # 3 Hard Inequality Limits (강한 부등식 제약: G * v <= h)
        # =====================================================================
        # 3.1. XML에 정의된 바에따라, 관절이 물리적인 가동 범위(Min, Max Joint)를 넘어가지 않도록 한계선을 그어줌
        self._limits = [mink.ConfigurationLimit(setup.model)]

        # 3.2. CLI 설정을 통해 관절 속도 제한이 지정된 경우 이를 추가함. 텔레옵 시 사람이 손을 너무 빠르게 움직이더라도 관절이 튀지 않고 지정된 최대 Angular Velocity 이하로 안전하게 꺾이도록 억제함
        if params.velocity_limits is not None:
            self._limits.append(mink.VelocityLimit(setup.model, params.velocity_limits))


        # =====================================================================
        # 4 Hard Equality Constraints (강한 등식 제약: A * v = b)
        # =====================================================================

        # 4.1 비활성 관절 (안 쓰는 가슴/머리/허리 등 추출)
        active_qpos: set[int] = set(setup.joint_resolver._right.arm_qpos.tolist()) | set(setup.joint_resolver._left.arm_qpos.tolist())

        freeze_dofs = [
            int(setup.model.jnt_dofadr[j])
            for j in range(setup.model.njnt)
            if setup.model.jnt_qposadr[j] not in active_qpos
        ]

        # 비활성 관절 속도를 0으로 강제 고정 (v_frozen = 0)
        self._freeze_task: mink.DofFreezingTask | None = (
            mink.DofFreezingTask(model=setup.model, dof_indices=freeze_dofs)
            if freeze_dofs
            else None
        )
        
        # =====================================================================
        # 5. Solver Options & State Control Variables
        # =====================================================================
        self._solver_params: dict = {"damping": params.damping}
        if params.diag_reg > 0.0:
            self._solver_params["diag_reg"] = params.diag_reg

        # 양팔의 목표 입력 수신 상태를 관리하기 위한 세트
        self._pending: set[str] = set(setup.sides)
        
        # 양쪽 그리퍼 각도/스트로크 값을 보관할 2차원 배열
        self._gripper = np.zeros(2, dtype=np.float32)

    def set_target(self, side: str, pose: np.ndarray) -> None:
        self._tasks[side].set_target(pose_to_se3(pose)) # 회전 값에 대한 차이를 구하기 위해서 Lie Algebra를 SE(3) 값으로 변환
        self._latest_targets[side] = np.asanyarray(pose[:3], dtype=np.float64) # 가장 최근에 받은 목표 위치 저장
        self._pending.discard(side) # 특정 side 에 대한 목표 값을 수신했음을 표시

    def sync(self, values16: np.ndarray) -> None:
        qpos = self._config.data.qpos.copy() # 현재 로봇의 joint 각도를 가져옴
        self._joint_resolver.set_qpos(qpos, values16[:8], "right") # Right 팔 joint 각도 설정
        self._joint_resolver.set_qpos(qpos, values16[8:16], "left") # Left 팔 joint 각도 설정
        self._config.update(q=qpos) # Driver에서 받은 값으로 MuJoCo 모델의 상태를 업데이트
        self._gripper[0] = values16[7] # Right 그리퍼 값 설정
        self._gripper[1] = values16[15] # Left 그리퍼 값 설정

    def ready(self) -> bool:
        return len(self._pending) == 0 # 모든 목표 값을 수신했는지 확인

    def solve(self) -> np.ndarray | None: 
        """QP 차분 IK를 풀고 최종 관절 제어 명령을 반환합니다."""

        # =====================================================================
        # 1. Soft Objectives 구성 [Tasks]
        # =====================================================================
        tasks = list(self._tasks.values())

        # 1.1 Reaching 상태(목표 거리가 threshold 이상) 판단하여 Posture 가중치 동적 스위칭
        if self._posture_cost > 0.0 or self._reach_posture_cost > 0.0:
            is_reaching = any(
                np.linalg.norm(target_pos) >= self._reach_threshold
                for target_pos in self._latest_targets.values()
            )
            current_cost = (
                self._reach_posture_cost if is_reaching else self._posture_cost
            )
            self._posture_task.set_cost(current_cost)
            tasks.append(self._posture_task)

        # =====================================================================
        # 2. Hard Equality Constraints 구성 [Constraints]
        # =====================================================================
        # 고정해야 할 관절이 존재하면 제약조건(Equality Constraint)으로 추가
        constraints = [self._freeze_task] if self._freeze_task else []

        # =====================================================================
        # 3. QP Solver 반복 호출
        # =====================================================================
        for _ in range(self._max_iters):
            
            try:
                # [Step 3-1] 1차 시도: 모든 안전 제약(Hard Limits)을 엄격히 준수하며 QP 해 탐색
                vel = mink.solve_ik(
                    configuration=self._config,
                    tasks=tasks,
                    dt=self._dt,
                    solver=self._solver_name,
                    limits=self._limits,  # 관절 가동 범위 및 각속도 제한 적용 (Hard Inequality)
                    constraints=constraints, # 비활성 관절 속도 0 고정 (Hard Equality)
                    safety_break=False,
                    **self._solver_params,
                )
            except mink.exceptions.NoSolutionFound:
                try: 
                    # [Step 3-2] 2차 시도 (Fallback): 제약이 너무 빡빡해 해가 없을 경우, Limits를 완화하여 재탐색
                    vel = mink.solve_ik( 
                        configuration=self._config,
                        tasks=tasks,
                        dt=self._dt,
                        solver=self._solver_name,
                        limits=[], 
                        constraints=constraints,
                        safety_break=False,
                        **self._solver_params,
                    )

                except mink.exceptions.NoSolutionFound:
                    # [Step 3-3] 예외 처리: 제약 완화 후에도 해 탐색 실패 시 이번 제어 스텝 건너뜀
                    print("Warning: IK solver failed (both constrained & unconstrained). Skipping step.")
                    return None

            # [Step 3-4] 관절 위치 업데이트: 구해진 관절 속도(vel)를 시간(dt) 동안 적분 (q_new = q_old + vel * dt)
            self._config.integrate_inplace(vel, self._dt)

        # =====================================================================
        # 4. 수신 상태 초기화 및 최종 16D 관절 제어 명령 가공 (Output Alignment)
        # =====================================================================
        
        self._pending = set(self._sides) # 양팔의 목표 입력 수신 완료 세트 리셋
 
        qpos = self._config.data.qpos # 수렴 완료된 최신 관절 위치(qpos) 추출

        # JointResolver를 사용해 오른쪽/왼쪽 팔의 구동기(Driver) 관절 각도만 분리
        right_joints, _ = self._joint_resolver.get_driver(qpos, "right")
        left_joints, _ = self._joint_resolver.get_driver(qpos, "left")

        return np.concatenate([
            np.append(right_joints, self._gripper[0]), 
            np.append(left_joints, self._gripper[1]),
        ]).astype(np.float32)

def _frame_name(setup: ArmSetup, side: str) -> str:
    return frame_name(setup.model, setup.frame_ids[side], setup.frame_types[side])

def _convert_velocity(
    rad_per_sec: float,
    dt: float,
    max_iters: int,
    tick_hz: float,
) -> float:
    if max_iters <= 0 or dt <= 0.0 or tick_hz <= 0.0:
        raise ValueError("max_iters, dt, and tick_hz must all be positive.")
    return rad_per_sec / (max_iters * dt * tick_hz)

def _load_velocity_caps(config_path: pathlib.Path | None) -> list[float]:
    """Return per-joint velocity caps in rad/s.

    With no config path, returns the built-in ARM_JOINT_VELOCITY_LIMITS_RAD_S. When a
    path is given, reads the top-level 'arm_velocity_limits' list from the YAML and uses
    it instead; the library stays config-format-agnostic beyond that single key.
    """
    if config_path is None:
        return ARM_JOINT_VELOCITY_LIMITS_RAD_S

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "arm_velocity_limits" not in data:
        raise ValueError(
            f"Config file {config_path} has no top-level 'arm_velocity_limits' list."
        )

    caps = [float(v) for v in data["arm_velocity_limits"]]
    expected = len(ARM_JOINT_VELOCITY_LIMITS_RAD_S)
    if len(caps) != expected:
        raise ValueError(
            f"arm_velocity_limits in {config_path} has {len(caps)} entries; "
            f"expected {expected}."
        )
    return caps


# ── CLI helpers ───────────────────────────────────────────────────────────────


def register_ik_args(parser: argparse.ArgumentParser) -> None:
    """Register IK-specific CLI flags. Call after register_common_args."""
    parser.add_argument(
        "--pos-cost", 
        type=float, 
        default=1.0, 
        help="Position task cost (default: 1.0)"
    )
    parser.add_argument(
        "--ori-cost",
        type=float,
        default=1.0,
        help="Orientation task cost (default: 1.0)",
    )
    parser.add_argument(
        "--lm-damping",
        type=float,
        default=0.01,
        help="Per-task LM damping (default: 0.01)",
    )
    parser.add_argument(
        "--damping",
        type=float,
        default=0.25,
        help="Global Tikhonov regularization (default: 0.25)",
    )
    parser.add_argument(
        "--solver", 
        default="daqp", 
        help="QP backend (default: daqp)"
    )
    parser.add_argument(
        "--max-iters", 
        type=int, 
        default=5, 
        help="IK iterations per event (default: 5)"
    )
    parser.add_argument(
        "--dt",
        type=float,
        default=0.1,
        help="Integration timestep per iteration (default: 0.1)",
    )
    parser.add_argument(
        "--posture-cost",
        type=float,
        default=0.01,
        help="Posture task weight for normal sign language motion, 0=disabled (default: 0.01)",
    )
    parser.add_argument(
        "--reach-posture-cost",
        type=float,
        default=0.001,
        help="Posture task weight when reaching/extending arm (default: 0.001)",
    )
    parser.add_argument(
        "--reach-threshold",
        type=float,
        default=0.35,
        help="Distance threshold in meters to trigger reaching posture cost (default: 0.35)",
    )
    parser.add_argument(
        "--diag-reg",
        type=float,
        default=0.0,
        help="QP diagonal regularization (default: 0.0)",
    )
    parser.add_argument(
        "--limit-velocity",
        action="store_true",
        help="Enable per-joint velocity limits (caps in config.ARM_JOINT_VELOCITY_LIMITS_RAD_S).",
    )
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        default=None,
        help=(
            "YAML file with a top-level 'arm_velocity_limits: [rad/s, ...]' list that "
            "overrides the built-in per-joint caps. Used only with --limit-velocity."
        ),
    )
    parser.add_argument(
        "--tick-hz",
        type=float,
        default=500.0,
        help="Dora tick rate in Hz; must match the dataflow timer (default: 500.0).",
    )

def ik_params_from_args(args: argparse.Namespace) -> IKParams:
    """Build IKParams from parsed args (requires register_ik_args to have been called)."""
    velocity_limits: dict[str, float] | None = None

    if args.limit_velocity:
        caps = _load_velocity_caps(getattr(args, "config", None))
        velocity_limits = {
            f"openarm_{side}_joint{i + 1}": _convert_velocity(
                rad_per_sec=v,
                dt=args.dt,
                max_iters=args.max_iters,
                tick_hz=args.tick_hz,
            )
            for side in ("left", "right")
            for i, v in enumerate(caps)
        }

    return IKParams(
        position_cost=args.pos_cost,
        orientation_cost=args.ori_cost,
        lm_damping=args.lm_damping,
        damping=args.damping,
        solver=args.solver,
        posture_cost=args.posture_cost,
        reach_posture_cost=getattr(args, "reach_posture_cost", 0.001),
        reach_threshold=getattr(args, "reach_threshold", 0.35),
        diag_reg=args.diag_reg,
        dt=args.dt,
        max_iters=args.max_iters,
        velocity_limits=velocity_limits,
    )

