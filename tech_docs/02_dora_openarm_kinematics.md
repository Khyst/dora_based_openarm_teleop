
## 1. 개요 및 모듈 목적
---
VR 수신기(`dora-openarm-vr`)가 전송한 End-Effector Target Pose를 통해, NANA v3 로봇의 14-DOF 양팔 관절 각도(Joint Angles)를 실시간으로 구해내기 위한 차분 역운동학 백엔드에 대한 Wrapper 역할인  `dora-openarm-kinematics` 노드를 정리합니다.

- **실행 노드명**: `dora-openarm-ik` (차분 역운동학), `dora-openarm-fk` (순운동학)
- **라이브러리 백엔드**: `dora_openarm_kinematics_control`

## 2. 핵심 연산 로직 및 동작 파라미터 명세
---
### 2.1 주요 IK 솔버 파라미터 (DAQP QP Backend)
---
> `dora-openarm-ik` 노드 구동 시 파이프라인 CLI 인자로 전달되는 핵심 솔버 파라미터 명세입니다.

| 파라미터 인자                    |         기본 설정값          |    수치 단위    | 기술적 역할 및 영향                                                |
| :------------------------- | :---------------------: | :---------: | :--------------------------------------------------------- |
| **`--xml`**                | `nana_v3_corrected.xml` |     경로      | 역운동학 계산의 기준이 되는 NANA v3 로봇 MuJoCo XML 파일                   |
| **`--mode`**               |       `bimanual`        |     문자열     | 연산 모드 (`bimanual` 양팔 동시 / `right` 오른팔 / `left` 왼팔)         |
| **`--max-iters`**          |          `10`           |  회 (Iters)  | IK 스텝당 최대 스무딩 QP 갱신 반복 횟수                                  |
| **`--dt`**                 |         `0.02`          | 초 (Seconds) | 차분 적분 타임스텝 (50Hz 속도 적분 수치 계산)                              |
| **`--damping`**            |          `0.3`          |    수치 계수    | Global Tikhonov Regularization 감쇄 계수 (특이점/Singularity 안정화) |
| **`--posture-cost`**       |         `0.05`          |     가중치     | 기본 중립 자세(Neutral Home Posture) 추종 작업 가중치                   |
| **`--reach-posture-cost`** |         `0.001`         |     가중치     | 작업 공간 한계 도달 시 자세 유연성을 위한 최소 가중치                            |
| **`--reach-threshold`**    |         `0.35`          |   미터 (m)    | 조작 반경 도달 감지 임계 거리                                          |
| **`--lm-damping`**         |          `0.1`          |    수치 계수    | Per-task Levenberg-Marquardt 감쇄 수치                         |

## 3. 데이터 처리 파이프라인 (Data Processing Pipeline)
---
> 수신된 EE Target Pose로부터 로봇 관절 각도가 산출되기 까지의 4단계 연산 파이프라인입니다.

### 3.1 1단계: PyArrow StructArray 디코딩
---
`extract_values()` 함수를 통해 Dora 데이터플로우 신호에서 PyArrow 구조체 `[{"pose": float32[8]}]`를 파싱하여 위치 $[p_x, p_y, p_z]$ 및 쿼터니언 $[q_w, q_x, q_y, q_z]$ 수치 추출.

### 3.2 2단계: mink QP Differential Solver 연산
---
- `Kinematics.set_target("right", pose_r)` 및 `Kinematics.set_target("left", pose_l)`을 호출하여 양팔의 목표 포즈 설정.
- DAQP QP 알고리즘으로 관절 가속도 및 속도 벡터를 실시간 이차계획법(Quadratic Programming)으로 해 도출.

### 3.3 3단계: 관절 가동 범위 및 속도 한계 제한
---
`nana_v3_corrected.xml`에 정의된 관절 범위(예: Joint 1 `-80° ~ +200°`, Joint 4 `0° ~ +140°`) 및 최대 관절 속도 한계를 오버슈트 없이 만족하도록 Clamping 처리.

### 3.4 4단계: PyArrow StructArray 인코딩 및 출력
---
`build_qpos_output()`을 호출하여 계산된 관절 각도를 `[{"qpos": float32[8]}]` PyArrow 구조체로 포맷팅하여 하류 노드로 전송.

## 4. Dora 노드 입출력 인터페이스 명세 (Inputs & Outputs)
---
### 4.1 Inputs
---

| Input ID             | 데이터 형식 (Type)            | 데이터 예시 (Example)                                                | 간단 설명 (Description)                              |
| :------------------- | :----------------------- | :-------------------------------------------------------------- | :----------------------------------------------- |
| **`tick`**           | `dora/timer/millis/2`    | `{"timestamp": 1723456789}`                                     | `quittable-tick-leader` 노드로부터 수신받는 250Hz 주기 틱 신호 |
| **`target_right`**   | `[{"pose": float32[8]}]` | `[{"pose": [0.15, 0.42, 0.98, 0.707, 0.0, 0.707, 0.0, 1.0]}]`   | `udp-receiver` 노드가 보낸 오른손 EE Target Pose 및 그리퍼값  |
| **`target_left`**    | `[{"pose": float32[8]}]` | `[{"pose": [-0.15, 0.42, 0.98, 0.707, 0.0, -0.707, 0.0, 1.0]}]` | `udp-receiver` 노드가 보낸 왼손 EE Target Pose 및 그리퍼값   |
| **`grip_right`**     | `float32`                | `1.0`                                                           | 오른손 중지 그립 입력값 (`0.0 ~ 1.0`)                      |
| **`grip_left`**      | `float32`                | `0.0`                                                           | 왼손 중지 그립 입력값 (`0.0 ~ 1.0`)                       |
| **`trigger_right`**  | `float32`                | `0.85`                                                          | 오른손 검지 트리거 입력값 (`0.0 ~ 1.0`)                     |
| **`trigger_left`**   | `float32`                | `0.0`                                                           | 왼손 검지 트리거 입력값 (`0.0 ~ 1.0`)                      |
| **`position_right`** | `[{"qpos": float32[8]}]` | `[{"qpos": [0.0, 0.1, 0.0, 0.5, 0.0, 0.0, 0.0, 1.0]}]`          | `follower-right` 하드웨어로부터 피드백받는 현재 오른팔 관절 상태      |
| **`position_left`**  | `[{"qpos": float32[8]}]` | `[{"qpos": [0.0, 0.1, 0.0, 0.5, 0.0, 0.0, 0.0, 1.0]}]`          | `follower-left` 하드웨어로부터 피드백받는 현재 왼팔 관절 상태        |

### 4.2 Outputs
---

| Output ID            | 데이터 형식 (Type)            | 데이터 예시 (Example)                                                  | 간단 설명 (Description)                                                 |
| :------------------- | :----------------------- | :---------------------------------------------------------------- | :------------------------------------------------------------------ |
| **`position_right`** | `[{"qpos": float32[8]}]` | `[{"qpos": [0.12, -0.34, 0.05, 0.82, -0.11, 0.04, 0.02, 1.0]}]`   | 연산된 오른팔 7축 관절 각도 + 그리퍼값 $\to$ `follower-right` / `mujoco-viewer` 전달 |
| **`position_left`**  | `[{"qpos": float32[8]}]` | `[{"qpos": [-0.12, -0.34, -0.05, 0.82, 0.11, 0.04, -0.02, 1.0]}]` | 연산된 왼팔 7축 관절 각도 + 그리퍼값 $\to$ `follower-left` / `mujoco-viewer` 전달   |
| **`status`**         | `string`                 | `"ready"`                                                         | IK 노드 정상 초기화 및 구동 알림 신호                                             |
