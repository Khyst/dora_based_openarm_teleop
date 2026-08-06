# VR Teleop 팔꿈치(Elbow) 추종 및 IK/입력 파이프라인 개선 가이드

- **작성일자**: 2026-08-05
- **대상 파이프라인**: `scripts/run_real.sh` (`dora-openarm-vr`, `dora-openarm-kinematics`)
- **참고 연구 패키지**: `src/researches/` (`TeleVision`, `xr_teleoperate`, `openarmx_teleop_vr`, `beavr-bot`)

---

## 1. 개요 및 현재 문제점 (Problem Statement)

현재 `run_real.sh` 실행 시 동작하는 Dora 기반 VR 원격제어 시스템은 Meta Quest 3 컨트롤러의 **손목(Wrist) 6D Pose만 수신 및 추종**하는 방식으로 작동합니다.

* **현상**: OpenArm과 같은 7-DOF 이상의 여유 자유도(Redundant Arm) 로봇은 손목 6D Pose(위치 3D + 자세 3D)만 구속할 경우, 팔꿈치 회전 각도(Swivel Angle)에 자유도가 남게 됩니다.
* **문제점**: 조종자(Operator)의 실제 팔꿈치 위치와 로봇의 팔꿈치 위치가 일치하지 않아 로봇 팔꿈치가 아래로 처지거나, 특정 포즈에서 엉뚱한 방향으로 뒤틀려 장애물/몸체와 충돌하거나, 관절 특이점(Singularity)에 빠지는 문제가 발생합니다.

본 문서는 `src/researches` 내 연구 코드베이스를 분석하여, 팔꿈치 추종 문제 해결 및 전체 VR Teleop 품질 향상을 위해 실도로 적용할 수 있는 구체적인 가이드라인을 제공합니다.

---

## 2. 연구 패키지별 분석 및 벤치마킹 요소 Summary

| 연구 패키지　　　　　　　| 특징 및 한계　　　　　　　　　　　　　　　　　　　　　　　 | 적용 가능한 핵심 기법　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　|
| :-------------------------| :-----------------------------------------------------------| :-----------------------------------------------------------------------------------------|
| **`TeleVision`**　　　　 | WebXR 기반 손가락 retargeting & 3D 비전 (팔꿈치 IK 미포함) | 손가락 Landmarks retargeting (`dex_retargeting`), WebXR 스트리밍　　　　　　　　　　　　 |
| **`xr_teleoperate`**　　 | Unitree 7-DOF 휴머노이드 VR teleop (
기본은 손목 IK)　　　　| **Head-Yaw Relative 참조계**, **Human-Robot Arm Scaling**, Pinocchio/CasADi IK Cost 구조 |
| **`openarmx_teleop_vr`** | OpenArmX 전용 ROS 2 VR teleop 패키지　　　　　　　　　　　 | **Relative Delta Pose (Clutching) 제어**, 관절별 Step Limit 안전 망　　　　　　　　　　　|
| **`beavr-bot`**　　　　　| MIT ARCLab의 다종 로봇 VR teleop & 데이터 수집　　　　　　 | **LeRobot 표준 데이터셋 수집 포맷**, 모듈화 아키텍처　　　　　　　　　　　　　　　　　　 |

---

## 3. 단계별 개선 및 적용 방안 (Step-by-Step Guide)

---

### Step 1. Quest 3 수신 및 전처리 단 개선 (`dora-openarm-vr`)

[`dora-openarm-vr/src/dora_openarm_vr/quest_receiver.py`](file:///home/khy/2.dora_based_openarm_teleop/src/nana_v3_dora_teleop_vr/dora-openarm-vr/src/dora_openarm_vr/quest_receiver.py)를 확장하여 좌표계 안정성 및 팔꿈치 정보를 확보합니다.

#### 1.1 Head-Yaw-Relative 참조계 적용 (`xr_teleoperate` 벤치마킹)
조종자가 고개를 위아래로 숙이거나 기울여도 로봇 기준계가 흔들리지 않도록 헤드셋의 Yaw(수평 회전) 축만을 기준으로 상대 좌표계를 정렬합니다.
```python
# Head Pose에서 Yaw 성분만 추출하여 참조계 생성
head_rot = Rotation.from_quat(q_head)
yaw, pitch, roll = head_rot.as_euler('zxy', degrees=False)
R_head_yaw = Rotation.from_euler('z', yaw)
```

#### 1.2 Human-to-Robot Arm Scaling (`scale_arms`)
조종자의 팔 길이(`L_human` ≈ 0.60m)와 OpenArm 로봇 팔 길이(`L_robot` ≈ 0.75m)의 비율을 스케일링합니다.
```python
scale_factor = L_robot / L_human
p_target_scaled = p_target_rel * scale_factor
```
> **효과**: 조종자가 팔을 다 펴기 전 로봇 팔이 먼저 완전히 펴지며 과도한 스트레인이나 특이점에 도달하는 현상을 막아줍니다.

#### 1.3 Relative Delta Control & Clutching (`openarmx_teleop_vr` 벤치마킹)
그립 버튼을 누른 시점의 컨트롤러 위치를 기준점(Zero Point)으로 잡고, 이동 변위(Delta Pose)만 로봇에 전달합니다.
```python
if grip_pressed and not WAS_GRIP_PRESSED:
    p_ref_ctrl = p_ctrl_current  # Clutching zero point
p_target = p_robot_home + (p_ctrl_current - p_ref_ctrl)
```
> **효과**: 조종자가 팔을 편안한 위치로 고정해두고 버튼을 뗏다 누르면서 로봇 팔꿈치 및 작업 범위를 재조정(Indexing)할 수 있습니다.

#### 1.4 Elbow 3D Position 추출 및 추정
* **방법 A (Quest 3 IOBT / Upper Body Tracking)**: Meta Quest 3 Body Tracking API를 통해 수신되는 `elbow` 3D 위치 패킷 파싱.
* **방법 B (신체 기하학적 추정)**: Head, Shoulder, Wrist 좌표를 바탕으로 기하학적 삼각측량(Triangulation) 및 Swivel Angle 기반 팔꿈치 위치 $P_{\text{elbow}}$ 계산.

---

### Step 2. IK Solver 단 확장 (`dora-openarm-ik`)

[`dora-openarm-ik/src/dora_openarm_kinematics/ik.py`](file:///home/khy/2.dora_based_openarm_teleop/src/nana_v3_dora_teleop_vr/dora-openarm-kinematics/src/dora_openarm_kinematics/ik.py)의 Mink QP Solver에 Multi-Task를 적용합니다.

#### 2.1 Multi-Task IK Formulation (Mink 연동)
Primary Task(손목 6D Pose)를 보장하면서, Secondary Task(팔꿈치 3D 위치)를 추종하도록 구성합니다.

```python
# 1. Primary Task: End-Effector (Wrist) 6D Pose Task
ee_task = mink.FrameTask(
    frame_name="openarm_wrist_link",
    position_cost=1.0,
    orientation_cost=1.0,
    lm_damping=0.1
)
ee_task.set_target(SE3_target_wrist)

# 2. Secondary Task: Elbow 3D Position Task (팔꿈치 추종)
elbow_task = mink.FrameTask(
    frame_name="openarm_elbow_link",
    position_cost=0.2,   # Primary Task보다 낮은 가중치 부여
    orientation_cost=0.0,
    lm_damping=0.1
)
elbow_task.set_target_position(P_target_elbow)

# 3. QP Solver에 Multi-Task 및 Posture/Limit Cost 적용
tasks = [ee_task, elbow_task, posture_task]
```

#### 2.2 관절별 스텝 제한 (Joint Step Limiters)
IK 계산 결과 Joint Angle 변화량이 과도할 경우 관절별 최대 허용 변화량(`max_step_deg`)으로 클리핑합니다.
```python
q_delta = np.clip(q_solved - q_current, -max_step_rad, max_step_rad)
q_final = q_current + q_delta
```

---

### Step 3. Dora Dataflow 설정 업데이트

[`config/dataflow-nana-teleop.yaml`](file:///home/khy/2.dora_based_openarm_teleop/src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop.yaml)에 팔꿈치 위치 데이터 채널을 추가 연결합니다.

```yaml
  - id: udp-receiver
    path: dora-openarm-quest-receiver
    outputs:
      - pose_right
      - pose_left
      - elbow_right   # 추가: 우측 팔꿈치 3D 위치
      - elbow_left    # 추가: 좌측 팔꿈치 3D 위치

  - id: ik
    path: dora-openarm-ik
    inputs:
      target_right: udp-receiver/pose_right
      target_left:  udp-receiver/pose_left
      elbow_right:  udp-receiver/elbow_right  # 추가
      elbow_left:   udp-receiver/elbow_left   # 추가
```

---

### Step 4. 모사학습 레코딩 파이프라인 확장 (`beavr-bot` 벤치마킹)

향후 VR 원격제어 데이터를 수집할 경우, `beavr-bot`의 `LeRobot` 파이프라인을 벤치마킹하여 관절 포즈, 카메라 이미지, 액션 데이터를 표준 `.parquet` / HDF5 형식으로 동기화 저장하도록 확장합니다.

---

## 4. 결론 및 구현 작업 로드맵

1. **1단계**: `dora-openarm-vr`의 `quest_receiver.py`에 Head-Yaw 좌표 정렬 및 Arm Scaling 기능 추가.
2. **2단계**: `dora-openarm-ik`의 `ik.py`에 Mink `elbow_task` (Secondary Position Task) 구현.
3. **3단계**: `dataflow-nana-teleop.yaml` 데이터 채널 업데이트 및 `run_real.sh` 실기기/Sim 테스트 진행.
