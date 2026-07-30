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

import numpy as np


def _slerp_quat(q1: np.ndarray, q2: np.ndarray, alpha: float) -> np.ndarray:
    dot = np.dot(q1, q2)
    if dot < 0.0:
        q2 = -q2
        dot = -dot
    if dot > 0.9995:
        res = q1 + alpha * (q2 - q1)
        return res / np.linalg.norm(res)

    theta_0 = np.arccos(dot)
    sin_theta_0 = np.sin(theta_0)
    theta = theta_0 * alpha
    sin_theta = np.sin(theta)

    s0 = np.cos(theta) - dot * sin_theta / sin_theta_0
    s1 = sin_theta / sin_theta_0
    return s0 * q1 + s1 * q2


class OneEuroPoseSmoother:
    """1 Euro Filter applied to position (adaptive cutoff) and rotation (SLERP)."""

    def __init__(
        self, min_cutoff: float = 10.0, beta: float = 0.8, d_cutoff: float = 1.0
    ):
        """ 
            파라미터
        """
        self.min_cutoff = min_cutoff 
        # min_cutoff (기본 값: 10.0, quest_receiver 인자: 2.0)
        # - 최소 차단 주파수 (Minimum Cutoff Frequency) : 손이 거의 멈춰 있거나 느리게 움직일 때 적용되는 필터링 기준 값. 이 값이 낮을수록 손떨림 노이즈가 더 강력하게 억제됨

        self.beta = beta
        # beta (기본 값 : 0.8, quest_reciever 인자 : 0.04)
        # - 속도 응답 계수 (Speed Coefficient) : 손이 빠르게 움직일 때 딜레이(Lag)를 줄이기 위한 반응성 파라미터. 이 값이 높을 수록 빠른 이동 시 딜레이 없이 즉각 반응 함

        self.d_cutoff = d_cutoff
        # d_cutoff (기본 값 : 1.0, quest_reciever 인자 : 1.5)
        # - 속도 필터 차단 주파수 (Derivative Cutoff Frequency) : 위치의 변화량(즉, 속도)을 필터링할 때 사용하는 차단 주파수

        """
            초기화
        """
        self.p_prev = None # 직전 프레임의 필터링된 3D 위치 벡터 [x, y, z]를 담는 변수 (초기엔 None)
        self.q_prev = None # 직전 프레임의 필터링된 3D 위치 벡터 [qw, qx, qy, qz]를 담는 변수(초기엔 None)
        self.t_prev = None # 직전 프레임의 처리 타임스탬프 시각(초 단위, 초기엔 기록 없음)
        self.dp_prev = np.zeros(3) # 직전 프레임의 3D 이동 속도 벡터(dx, dy, dz)(초기엔 모든 요소를 0으로 초기화)

    def reset(self) -> None:
        """Clear state so next sample is treated as a fresh start (call on INVALID→valid transition)."""
        self.p_prev = None
        self.q_prev = None
        self.t_prev = None
        self.dp_prev = np.zeros(3)

    def smooth(self, t: float, target_pose: np.ndarray | None) -> np.ndarray | None:
        
        if target_pose is None:
            return None

        t_p = target_pose[0:3] # 7차원 quest_reciever 검출 포즈 중 앞쪽 3개 원소인 3D 위치 벡터
        t_q = target_pose[3:7] # 7차원 quest_reciever 검출 포즈 중 뒤쪽 4개 원소인 4D 회전 쿼터니언 벡터

        if self.t_prev is None or self.p_prev is None: # 첫 수신 처리(초기화/리셋후)
            self.p_prev = t_p.copy() # 입력 받은 포즈를 그대로 복사 할당
            self.q_prev = t_q.copy() # 입력 받은 포즈를 그대로 복사 할당
            self.t_prev = t # 전달 받은 timestamp를 할당 (이건 왜 copy() 안함?)
            return target_pose.copy() # 그대로 반환

        dt = t - self.t_prev # 이전 시간과 지금 시간 (Delta)
        if dt <= 0.0: # 시간이 흐르지 않았을 경우 
            return target_pose.copy() # 그대로 반환

        def get_alpha(dt: float, cutoff: float) -> float: # Euro Filter의 핵심인 지수 이동 평균 (EMA) 가중치 a를 구하는 수식 함수 <- 이 함수에 대한 따로 파라미터별 효과에 대해 docs로 정리할 필요 존재
            tau = 1.0 / (2 * np.pi * cutoff)
            return 1.0 / (1.0 + tau / dt)

        dp_raw = (t_p - self.p_prev) / dt # 위치 변화율 -> 3D 이동 속도 벡터
        alpha_d = get_alpha(dt, self.d_cutoff) # d_cutoff와 dt에 따른 가중치 할당 (parameter: d_cutoff)
        dp_filtered = alpha_d * dp_raw + (1.0 - alpha_d) * self.dp_prev # 튀는 노이즈 속도를 지우기 위해 속도 벡터 자체에도 지수 이동 평균 필터를 적용한 노이즈가 제거된 속도 벡터
        
        """
            적응형 차단 주파수 계산 (OneEuroFilter의 핵심)
            - 손이 느리게 움직일 때 -> speed가 0에 수렴 : cutoff_p가 작아짐 -> alpha가 0에 가까워짐 -> 손 떨림 노이즈를 매우 강력하게 보정
            - 손이 빠르게 움직일 때 -> speed가 큼 : cutoff_p가 커짐 -> alpha가 1에 가까워짐 -> 필터를 약하게 하여 딜레이(Lag) 없이 바로 손을 따라옴
        """
        speed = np.linalg.norm(dp_filtered) # 필터링된 3D 속도 벡터의 크기(스칼라 속력, m/s)
        cutoff_p = self.min_cutoff + self.beta * speed  
        alpha_p = get_alpha(dt, cutoff_p)

        p_hat = self.p_prev + alpha_p * (t_p - self.p_prev) # 위치 벡터 선형 보간
        q_hat = _slerp_quat(self.q_prev, t_q, alpha_p) # 쿼터니언 회전 구면 선형 보간 (SLERP : Spherical Linear Interpolation)

        # 필터링 완료된 위치, 회전, 속도, 현재 시각을 이전 상태 변수에 저장하여 다음 프레임 연산을 준비
        self.p_prev = p_hat 
        self.q_prev = q_hat 
        self.dp_prev = dp_filtered
        self.t_prev = t

        return np.array(
            [p_hat[0], p_hat[1], p_hat[2], q_hat[0], q_hat[1], q_hat[2], q_hat[3]], # 노이즈가 보정된 최종 위치 3개와 쿼터니언 4개를 결합하여 최종 포즈로 반환
            dtype=np.float32,
        )
