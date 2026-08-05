# 수화(Sign Language) 휴머노이드 로봇 Teleoperation IK 제어기 구축 설계

- **작업 일자**: 2026-08-05
- **작업 분류**: Docs / Architecture Design

---

## 1. 개요 및 목적
수화(Sign Language) 동작 재현을 위한 휴머노이드 로봇 Teleoperation 제어기 구축 기술 요점 및 팔꿈치(Elbow) 좌표/자세를 Inverse Kinematics(IK)에 결합하여 인간다운 자연스러운 팔 동작(Humanlike Motion)을 구현하는 기술 아키텍처 및 연구/오픈소스 참조 가이드를 정리한다.

---

## 2. 주요 내용 및 설계 사항

### 2.1. 문제의 본질 (Problem Framing)
1. **기존 구조의 한계**:
   - 기존 `dora-openarm` 및 단일 IK 파이프라인은 손목(End-Effector, EE)의 6DoF Pose 추종에만 집중되어 있음.
2. **도메인 특수성**:
   - 수화(Sign Language)는 손끝의 위치뿐만 아니라 어깨의 들림, 팔꿈치 벌어짐 각도(Swivel Angle), 팔 전체의 자태(Form) 자체가 언어적 의미를 가짐.
3. **단일 EE IK의 한계 (Chicken-wing 현상)**:
   - 손목 위치/자세만 IK로 해결할 경우, 로봇은 수학적으로 최적인 해를 찾지만 팔꿈치가 아래로 처지거나 밖으로 튀어나오는 등 수화의 표상성(Representativeness)이 손실됨.

---

### 2.2. 시스템 및 센서 구조 (Meta Quest 3 IOBT 활용 전략)
- **어깨 (Shoulder)**:
  - 로봇 Base(Torso)에 위치가 고정된 회전 중심점(Origin).
  - IK 이동 목표(Task)로 직접 투입하지 않고, 상대 좌표계의 원점(Reference Frame)으로 활용.
- **팔꿈치 (Elbow) & 손목 (Wrist)**:
  - Meta Quest 3의 Inside-Out Body Tracking(IOBT)으로 도출된 상대 3D 위치 및 Pose를 `mink` QP 솔버의 Multi-Task로 등록.
  - **Main Task**: 손목 Pose 추종 (`position_cost = 1.0`, `orientation_cost = 1.0`)
  - **Sub Task**: 팔꿈치 Position 추종 (`position_cost = 0.3 ~ 0.5`, `orientation_cost = 0.0`)
- **결과 효과**:
  - 손목의 정밀한 6D 위치를 보장하면서, 어깨 관절각(3자유도)은 팔꿈치와 손목의 3D 공간 배치를 만족시키는 최적의 각도로 자동 역산되어 인간의 자연스러운 수화 폼을 복원함.

---

### 2.3. 참고 연구 및 오픈소스 프로젝트

#### 1) Humanlike IK & Two-Tracker Teleoperation 연구
- **논문**: *"Humanlike Inverse Kinematics for Improved Spatial Awareness in Construction Robot Teleoperation"* (ASCE Journal, 2024 / 2025)
- **핵심 내용**: 단일 End-Effector IK의 팔꿈치 튀어나옴 현상을 해결하기 위해 2개의 트래커(End-Effector + Middle Joint/Elbow)를 사용해 IK를 푸는 Humanlike IK 알고리즘 제안.
- **시사점**: 2-Point Target IK가 사람의 팔 동작을 복원하고 조종자의 공간 인지성을 향상시킴을 수학적/실험적으로 증명.

#### 2) OPEN TEACH (Versatile Teleoperation Framework)
- **오픈소스 저장소**: GitHub (`open-teach` / NYU / Meta AI 연구진)
- **핵심 내용**: VR 기기(Meta Quest 시리즈 등)를 활용한 로봇 팔 및 다자유도 핸드 원격 제어 프레임워크.
- **시사점**: Quest 3의 VR 핸드/바디 추적 데이터를 로봇 Kinematics 좌표계로 리타게팅(Retargeting)하는 브릿지 코드 파이프라인 제공.

#### 3) Pink / mink QP 기반 Multi-Task IK 오픈소스
- **오픈소스 저장소**: `kevinzakka/mink` (MuJoCo 기반) / Pink (Pinocchio 기반)
- **핵심 내용**: 다중 프레임(Multi-Frame Task)을 단일 QP 최적화 문제로 합성하여 실행.
- **활용 방법**: Unitree G1/H1, Apptronik Apollo 예제와 같이 손목(EE), 팔꿈치, 발목, Pelvis 좌표를 동시에 Task 배열(`tasks = [wrist_task, elbow_task, posture_task]`)로 전달하는 메커니즘 활용.

#### 4) Swivel Angle / Arm Retargeting 구현체
- **프로젝트**: AnyTeleop / DexCap / Teleop-Anything
- **핵심 내용**: 어깨-팔꿈치-손목이 이루는 평면의 Swivel Angle(벌어짐 각도)을 산출하여 7DoF 중복 가동 로봇의 Redundancy Resolution 제약 조건으로 주입하는 파이썬 알고리즘 포함.

---

### 2.4. 수석 엔지니어 가이드라인 (코드 확장 계획)

1. **`kinematics.py`의 `_IKSolver` 클래스 확장**:
   ```python
   # _IKSolver __init__ 내부
   self._elbow_tasks = {
       side: mink.FrameTask(
           frame_name=f"{side}_elbow_link",
           frame_type="body",
           position_cost=params.elbow_position_cost, # 예: 0.3 ~ 0.5
           orientation_cost=0.0
       ) for side in setup.sides
   }
   ```
2. **Quest 3 데이터 처리 파이프라인 수립**:
   - Quest 3의 어깨 좌표를 원점(Origin)으로 삼음.
   - 어깨 좌표계 기준 팔꿈치 3D 벡터($\mathbf{P}_{\text{elbow}}$) 및 손목 6D Pose($\mathbf{T}_{\text{wrist}}$)를 스케일링 후 `set_target`에 주입.
3. **IK 실행 시 Task 합성 및 풀이**:
   ```python
   tasks = [wrist_task, elbow_task, posture_task]
   # mink.solve_ik()를 호출해 단일 QP 최적화로 처리
   ```

---

## 3. 테스트 및 승인 내용
- **문서화 승인**: 요청된 수화 휴머노이드 로봇 Teleoperation 제어기 기술 요점 및 구현 가이드라인 정리 완료.
- **향후 과제**: `kinematics.py` 및 Meta Quest 3 수신 브릿지 파이프라인에 팔꿈치 Task 적용 후 시뮬레이션/실기기 검증 진행 예정.
