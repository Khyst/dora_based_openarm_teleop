# Dora OpenArm & Kinematics IK Parameter & Pipeline Guide

- **작업 일자**: 2026-08-03
- **작업 분류**: Docs / Update
- **연관 파일**: 
  - [`openarm_control/kinematics.py`](file:///.venv/lib/python3.14/site-packages/openarm_control/kinematics.py)
  - [`dora-openarm-kinematics/src/dora_openarm_kinematics/ik.py`](file:///src/nana_v3_dora_teleop_vr/dora-openarm-kinematics/src/dora_openarm_kinematics/ik.py)
  - [`dataflow-nana-teleop.yaml`](file:///src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop.yaml)

---

## 1. 개요 및 목적
본 문서는 `openarm_control` 패키지의 `kinematics.py` 모듈과 `dora-openarm-kinematics` (`ik.py`) 노드가 `dataflow-nana-teleop.yaml` 파이프라인 환경에서 텔레옵(Teleoperation)을 수행할 때 Inverse Kinematics(IK, 역운동학)가 도출되는 구조적 메커니즘을 정의하고, IK 솔버 수치 제어 및 안정성 튜닝을 위한 핵심 파라미터 가이드를 제공합니다.

---

## 2. Teleop 파라인 역운동학(IK) 도출 방식

`dataflow-nana-teleop.yaml` 기반 실시간 텔레오퍼레이션 파이프라인에서 IK 도출 흐름은 다음과 같습니다.

### 2.1 전체 파이프라인 데이터 흐름
```
[VR Controller / Quest Receiver] 
       │ (target_right/left: 8D Pose [x,y,z,qw,qx,qy,qz,gripper])
       │ (grip_right/left: Float Clutch Signal)
       ▼
[dora-openarm-ik (ik.py)] ◄─── (position_right/left: 8D Feedback Sync) ─── [OpenARM Follower / Driver]
       │ 
       │  mink QP-based Differential IK Solver (kinematics.py)
       ▼ 
(position_right/left: 8D Target Joint Angles)
       │
       ├──► [OpenARM Driver (follower-right / follower-left)]
       └──► [MuJoCo Simulator / Viewer]
```

### 2.2 IK 도출 4단계 메커니즘
1. **클러치(Clutch) 및 입력 수신**:
   - `udp-receiver` 노드에서 전달받은 `grip_right` / `grip_left` 버튼 신호를 검사합니다 (`grip > 0.5`).
   - 사용자가 그립 버튼을 누르고 있는 동안에만 컨트롤러 8D 포즈(`target_right`, `target_left`)를 IK 타겟으로 업데이트합니다. (손을 놓으면 이전 관절 상태 유지)
2. **실시간 관절 동기화 (`kin.sync()`)**:
   - 하드웨어/시뮬레이터(`follower-right`, `follower-left`)의 현재 관절 위치(`position_right/left`)를 피드백받아 `Kinematics.sync()`를 호출하고, mink `Configuration` 내부 $q_{pos}$ 값을 실시간 동기화합니다.
3. **Mink QP 미분 IK 풀이 (`kin.solve()`)**:
   - 8D 포즈 중 앞의 7D 포즈(`[px, py, pz, qw, qx, qy, qz]`)를 `pose_to_se3()`를 통해 SE(3) 변환 매트릭스로 전환하여 `mink.RelativeFrameTask` (기준 프레임 `arm_origin` site 대상)에 전달합니다.
   - 설정된 타임스텝(`dt`)과 최대 반복 횟수(`max_iters`) 동안 QP (Quadratic Programming) 이차계획법 솔버(`daqp` 등)를 통해 관절 속도 벡터 $\dot{q}$를 계산하고 $q_{next} = q + \dot{q} \cdot dt$ 로 적분(integration)합니다.
4. **결과 변환 및 출력 발행**:
   - 7개 관절 각도와 그립 각도 1개를 결합하여 팔당 8D float32 배열(`[q0~q6, gripper_q]`)을 만든 뒤, PyArrow 구조체(`build_qpos_output()`) 형태로 `position_right`, `position_left` 노드 출력을 발행합니다.

---

## 3. `openarm_control` `kinematics.py` 내부 IK 파라미터 가이드

`openarm_control/kinematics.py` 파일의 `IKParams` 데이터 클래스는 Mink QP IK 솔버의 동작 속성을 제어합니다.

### 3.1 파라미터 상세 요약 표

| CLI 파라미터 | `IKParams` 변수 | 기본값 | 주요 역할 | 튜닝 가이드 및 효과 |
| :--- | :--- | :--- | :--- | :--- |
| **`--pos-cost`** | `position_cost` | `1.0` | 손끝 3D 위치(Position) 추종 가중치 | • 높이면 목표 위치에 더 정확히 도달함.<br>• 회전보다 위치 정확도가 중요할 때 증가. |
| **`--ori-cost`** | `orientation_cost` | `1.0` | 손끝 3D 자세(Orientation) 추종 가중치 | • 높이면 컨트롤러의 회전 각도를 엄격하게 쫓아감. |
| **`--lm-damping`** | `lm_damping` | `0.01` | Levenberg-Marquardt 감쇄 계수 | 🌟 **특이점(Singularity) 방어 핵심**<br>• 팔이 일자로 펴질 때 관절 속도가 발산하는 것을 억제.<br>• 높이면(`0.1 ~ 0.3`) 특이점에서 부드럽게 멈춤. |
| **`--damping`** | `damping` | `0.25` / `1.0` | 전역 Tikhonov 관절 속도 감쇄력 | • 높이면(`1.0 ~ 2.0`) 미세 잔여 떨림이 사라지고 부드러워짐.<br>• 낮추면(`0.1`) 추종 반응이 민첩해지나 덜덜거릴 수 있음. |
| **`--posture-cost`**| `posture_cost` | `0.01` | 중립 기본 자세(Home) 유지 가중치 | • 높이면(`0.05 ~ 0.1`) 팔꿈치가 꺾이지 않고 자연스러운 홈 포즈를 유지하려 함.<br>• `0` 설정 시 끄기 가능. |
| **`--dt`** | `dt` | `0.1` / `0.02` | 미분 적분 시간 간격 | • Dataflow timer 주기(50Hz ➔ `0.02`)와 일치해야 속도 적분이 정확함. |
| **`--max-iters`** | `max_iters` | `5` / `10` | 1스텝 당 최대 QP 연산 횟수 | • 높이면(`10 ~ 20`) 도달 정밀도 향상.<br>• 낮추면(`5`) 실시간 연산 속도 향상 및 CPU 사용량 감소. |
| **`--solver`** | `solver` | `"daqp"` | QP 이차계획법 솔버 백엔드 | • `"daqp"`, `"osqp"`, `"proxqp"` 지원. 실시간 텔레옵에는 `daqp` 권장. |
| **`--limit-velocity`**| `velocity_limits`| `False` | 관절 최대 제한 속도(Velocity Limit) 강제 | • 활성화 시 하드웨어 한계 속도를 초과하는 튀는 동작 차단. |

---

## 4. 트러블슈팅 및 현상별 파라미터 튜닝 시나리오

### 🚨 시나리오 1: 팔을 쫙 뻗었을 때 로봇 팔 관절이 순간적으로 튀거나 발산할 때
- **원인**: 로봇 특이점(Singularity) 경계에 도달하여 미분 IK의 관절 속도 역행렬 연산이 과도해짐.
- **조치 방안**:
  - `--lm-damping`을 `0.01`에서 **`0.1 ~ 0.2`로 증가**.
  - `--posture-cost`를 `0.01`에서 **`0.05`로 증가**시켜 팔꿈치 꺾임 방지.

### 🐢 시나리오 2: 손 이동 시 로봇 팔 추종이 느리고 둔하게 쫓아올 때
- **원인**: Tikhonov 감쇄력(`--damping`)이 너무 높거나 `max-iters` 횟수가 부족함.
- **조치 방안**:
  - `--damping`을 `1.0`에서 **`0.25 ~ 0.5`로 감소**.
  - `--max-iters`를 `5`에서 **`10 ~ 15`로 증가**.

### 📳 시나리오 3: 손을 정지하고 있는데 로봇 팔 관절이 떨릴 때
- **원인**: 수신되는 타겟 포즈의 미세 센서 노이즈를 IK 솔버가 과도하게 정밀하게 추종하려 함.
- **조치 방안**:
  - `--damping`을 **`1.0 ~ 1.5`로 증가**시켜 필터링 효과 부여.

---

## 5. `dataflow-nana-teleop.yaml` 파이프라인 실제 노드 설정 예시

```yaml
  - id: ik
    build: pip install -e ../../dora-openarm-kinematics
    path: dora-openarm-ik
    args: "--xml ../../../nana_v3_description/assets/robot/urdf/nana_v3_corrected.xml --mode bimanual --max-iters 10 --dt 0.02 --damping 1.0 --posture-cost 0.01 --lm-damping 0.1"
    inputs:
      tick: quittable-tick-leader/tick
      target_right: udp-receiver/pose_right
      target_left:  udp-receiver/pose_left
      grip_right:   udp-receiver/grip_right
      grip_left:    udp-receiver/grip_left
      position_right: follower-right/position
      position_left: follower-left/position
    outputs:
      - position_left
      - position_right
      - status
```

---

## 6. 테스트 및 승인 내용
- **검증 내용**: `openarm_control/kinematics.py`, `dora_openarm_kinematics/ik.py` 소스 코드 분석 및 `dataflow-nana-teleop.yaml` 파이프라인 데이터 흐름 분석 완료.
- **결과**: IK 도출 메커니즘 4단계 정리 및 9개 핵심 파라미터 가이드, 트러블슈팅 시나리오 문서화 완료.
