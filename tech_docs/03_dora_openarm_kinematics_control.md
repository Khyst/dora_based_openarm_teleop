## 1. 개요 및 모듈 목적
---
본 문서는 `nana_openarm_teleop` 시스템의 핵심 운동학 연산 백엔드 엔진인 `dora-openarm-kinematics-control` (`dora_openarm_kinematics_control`) 패키지의 수학적 이론, mink 라이브러리 기반 이차계획법(QP) 최적화 제어 알고리즘, 및 파이썬 API 구조를 상세히 정리합니다.

## 2. mink를 통한 Target Pose 기반 Joint Values 도출 활용 방향
---
`mink`는 로봇의 ==현재 형상(Configuration)과 작업 공간(Task space) 내 목표(Objective)==들이 주어졌을 때, ==설정된 제약조건(Constraints & Limits)을 엄격히 준수==하면서 목표를 최적으로 만족하는 ==관절 속도(Joint Velocity)==를 산출하는 ==차분 역운동학(Differential IK) 라이브러리입==니다.

### 2.1 개념 및 제어 방식 (Task & Constraint)
---
`mink`는 매 제어 스텝(Control Step)마다 역운동학 문제를 ==**이차계획법(QP, Quadratic Programming)** 문제로 정형화하여 **지역적 최적해(Locally optimal joint velocity)**== 를 도출합니다.

- **작업 목표 (Tasks / Soft Objectives)**: ==로봇이 수행해야 하는 작업== 
	- 예: End-Effector의 목표 포즈 도달, 기본 자세 유지, 질량 중심 제어 등
- **제약 조건 (Limits / Hard Constraints)**: ==로봇이 절대 침범해서는 안 되는 물리적 한계== 
	- 예: 관절 가동 범위 초과 방지, 관절 속도 제한, 특정 자유도 고정 등

### 2.2 주요 특징 (Key Features)
---
1. **조합 가능한 작업 추상화 (Composable Task Abstraction)**
   - 작업 공간에서의 ==복수 목표(예: 말단 포즈 추종, 널스페이스 자세 유지 등)를 개별 태스크로 정의하고, 단일 최적화 스텝에서 통합 연산==합니다.
1. **원활한 제약조건 처리 (Graceful Constraint Handling)**
   - ==목표(Objectives)와 제약조건(Constraints)==을 ==하나의 QP 최적화 문제로 결합==하여, 제약 간 충돌이 발생하거나 완전한 만족이 불가능한 상황에서도 ==합리적인 트레이드오프(Trade-off)를 유도==합니다.
1. **실시간 제어 최적화 (Designed for Real-time Control)**
   - ==제어 주기(Control Rate) 내에서 유연하게 작동하는 고속 수치 솔버(Solver)==를 제공하여 실시간 로봇 제어 루프에 최적화되어 있습니다.

### 2.3 Mink 활용 예제 코드 (Mink Example Tutorial)
---

```python
import numpy as np
import mujoco
from mink import (
    Configuration, 
    FrameTask, 
    PostureTask, 
    ConfigurationLimit, 
    DofFreezingTask, 
    SE3, 
    solve_ik
)

# 1. MuJoCo 모델 및 Configuration 초기화
model = mujoco.MjModel.from_xml_path("robot.xml")
config = Configuration(model)

# -------------------------------------------------------------
# 1. Soft Objectives (약한 제약: 오차 최소화 목표)
# -------------------------------------------------------------
# ① End-Effector 위치 맞추기 Task (Primary Task)
ee_task = FrameTask(frame_name="ee", frame_type="site", position_cost=1.0)
ee_task.set_target(SE3.from_translation([0.5, 0.0, 0.3]))

# ② 기본 자세 유지 Task (Null-space Posture Task)
posture_task = PostureTask(model, cost=1e-3)
posture_task.set_target(config.data.qpos.copy())

tasks = [ee_task, posture_task]

# -------------------------------------------------------------
# 2. Hard Limits (강한 부등식 제약: G * v <= h)
# -------------------------------------------------------------
# 관절이 물리적 가동 범위(Min/Max Joint Limit)를 넘지 않도록 절대 차단
limits = [ConfigurationLimit(model)]

# -------------------------------------------------------------
# 3. Hard Constraints (강한 등식 제약: A * v = b)
# -------------------------------------------------------------
# 예: 0번 관절(허리/베이스 등)의 속도를 0으로 엄격하게 고정 (v_0 = 0)
freeze_task = DofFreezingTask(model=model, dof_indices=[0])
constraints = [freeze_task]

# -------------------------------------------------------------
# 4. 차분 IK 수렴 루프 (Differential IK Loop)
# -------------------------------------------------------------
max_iters = 5
dt = 0.01

for _ in range(max_iters):
    vel = solve_ik(
        configuration=config,
        tasks=tasks,             # Soft Objectives (약한 제약)
        limits=limits,           # Hard Inequality (강한 부등식 제약)
        constraints=constraints, # Hard Equality (강한 등식 제약)
        dt=dt,
        solver="daqp",
        damping=1e-6,
    )
    
    # 관절 속도(vel) 기반 위치 업데이트: q_new = q_old + vel * dt
    config.integrate_inplace(vel, dt=dt)
```


## 3. mink의 수학적 및 이론적 배경 (Mathematical Foundations)
---
### 3.1 차분 역운동학(Differential IK) 및 QP 수식화
---
로봇의 **현재 관절 각도를 $\mathbf{q} \in \mathbb{R}^n$, 말단 포즈를 $\mathbf{x} \in \mathbb{R}^6$, 자코비안 행렬을 $\mathbf{J}(\mathbf{q}) = \frac{\partial \mathbf{x}}{\partial \mathbf{q}}$라 할 때**, 차분 역운동학은 원하는 **말단 속도 $\dot{\mathbf{x}}_{\text{target}}$을 만족하는 관절 속도 $\dot{\mathbf{q}}$를 구하는 문제**입니다.

본 라이브러리는 이를 ==**이차계획법(QP, Quadratic Programming)**== 문제로 정형화하여 **매 스텝 최적의 $\dot{\mathbf{q}}$를 도출**합니다: 

$$\min_{\dot{\mathbf{q}}} \quad \frac{1}{2} \|\mathbf{J}(\mathbf{q}) \dot{\mathbf{q}} - \dot{\mathbf{x}}_{\text{target}}\|_{\mathbf{W}_x}^2 + \frac{1}{2} \lambda \|\dot{\mathbf{q}}\|^2 + \frac{1}{2} w_{\text{posture}} \|\dot{\mathbf{q}} - \dot{\mathbf{q}}_{\text{posture}}\|_{\mathbf{W}_q}^2$$

$$\text{subject to} \quad \mathbf{q}_{\text{min}} \le \mathbf{q} + \dot{\mathbf{q}} \Delta t \le \mathbf{q}_{\text{max}} \quad \text{(Configuration Limit)}$$

$$\quad -\dot{\mathbf{q}}_{\text{max}} \le \dot{\mathbf{q}} \le \dot{\mathbf{q}}_{\text{max}} \quad \text{(Velocity Limit)}$$

### 3.2 수치 특이점 회피 (Tikhonov & Levenberg-Marquardt Damping)
---
로봇 팔이 일직선으로 쫙 펴지거나 무릎/어깨 관절이 꺾이는 특이점(Singularity) 근처에서는 역행렬 수치가 무한대로 발산할 위험이 있습니다.

- **Damping 계수 ($\lambda$, `damping=0.25`)**: Tikhonov 정규화 항을 통해 특이점 근처에서 관절 속도가 과도하게 폭발하는 현상을 억제하고 관절 움직임을 안정화시킵니다.
- **LM Damping (`lm_damping=0.01`)**: Levenberg-Marquardt 적응형 감쇄를 태스크 단위로 적용하여 연산 안정성과 포즈 정밀도의 균형을 유지합니다.


## 4. 핵심 클래스 및 파라미터 구조 명세
---
### 4.1 `ArmSetup` 데이터 구조 파라미터 명세
---
FK, IK 및 노드 전반에서 공유하는 MuJoCo 기하 모델/동역학 데이터 컨텍스트 구조체입니다.

| 파라미터 명칭              |    파이썬 데이터 타입    |         기본값 / 설정 예시         | 기술적 설명 및 역할                                           |
| :------------------- | :--------------: | :-------------------------: | :---------------------------------------------------- |
| **`model`**          | `mujoco.MjModel` |     NANA v3 MjModel 객체      | NANA v3 로봇 강체, 관절, 메쉬 기하 데이터 모델                       |
| **`data`**           | `mujoco.MjData`  |         MjData 인스턴스         | 현재 관절 각도(`qpos`), 관절 속도(`qvel`), 가속도 및 렌더링 프레임 상태     |
| **`joint_resolver`** | `JointResolver`  |     OpenArm v2 Resolver     | 14축 양팔 관절 인덱스(qpos address) 매핑 및 `set_qpos()` 직결 유틸리티 |
| **`sides`**          |   `list[str]`    |     `["right", "left"]`     | 현재 IK/FK 연산 대상이 되는 활성 팔 명단                            |
| **`frame_ids`**      | `dict[str, int]` | `{"right": id, "left": id}` | 팔별 End-Effector 기준 프레임의 MuJoCo 객체 ID 번호               |
| **`frame_types`**    | `dict[str, str]` |  `{"right": "site", ...}`   | EE 프레임의 오브젝트 종류 (`"site"`, `"body"`, `"geom"`)        |
| **`origin_id`**      |  `int \| None`   |    `arm_origin` site ID     | 텔레옵 포즈 연산의 기준 원점 ID (`None` 지정 시 World 절대 원점)         |
| **`origin_type`**    |      `str`       |          `"site"`           | 기준 원점 프레임의 오브젝트 종류                                    |

### 4.2 `IKParams` 데이터클래스 파라미터 명세
---
IK 솔버 구동 시 최적화 행렬 가중치와 제약조건을 정의하는 파라미터 구조체입니다.

| 파라미터 명칭                  |  타입   |    기본값     | 수치 의미 및 기술적 영향                              |
| :----------------------- | :---: | :--------: | :------------------------------------------ |
| **`position_cost`**      | float |   `1.0`    | End-Effector 3D 위치($px, py, pz$) 추종 가중치     |
| **`orientation_cost`**   | float |   `1.0`    | End-Effector 3D 회전($qw, qx, qy, qz$) 추종 가중치 |
| **`damping`**            | float |   `0.25`   | Global Tikhonov Regularization 특이점 감쇄 계수    |
| **`lm_damping`**         | float |   `0.01`   | Per-task Levenberg-Marquardt 대각 정규화 계수      |
| **`solver`**             |  str  |  `"daqp"`  | QP 최적화 수치 솔버 이름 (`daqp` 사용)                 |
| **`posture_cost`**       | float |   `0.01`   | 널스페이스(Null-space) 기본 중립 자세 유지 가중치           |
| **`reach_posture_cost`** | float |  `0.001`   | 먼 거리 도달 시 유연성을 위한 최소 자세 가중치                 |
| **`reach_threshold`**    | float | `0.35` (m) | 조작 반경 도달 감지 임계 거리 (35cm 이상 시 유연 가중치 전환)     |
| **`dt`**                 | float | `0.1` (s)  | 1스텝 당 수치 적분 시간 간격                           |
| **`max_iters`**          |  int  |    `5`     | 매 제어 주기당 internal QP 갱신 최대 반복 횟수            |

### 4.3 `Kinematics` 파이썬 API 명세
---
사용자 노드가 직접 호출하여 FK/IK 연산을 구동하는 핵심 클래스 API입니다.

| 메서드 명칭                       | 입력 인자 (Arguments)                 | 반환값 (Return)                    | 기능 및 동작 상세                                                        |
| :--------------------------- | :-------------------------------- | :------------------------------ | :---------------------------------------------------------------- |
| **`fk(side, joints)`**       | `side: str`, `joints: float32[8]` | `float32[7]`                    | 지정한 한쪽 팔(`"right"`/`"left"`)의 관절 각도로 순운동학을 수행하여 7D EE Pose 반환     |
| **`fk_bimanual(r, l)`**      | `r: float32[8]`, `l: float32[8]`  | `tuple[float32[7], float32[7]]` | 한 번의 `mj_forward` 호출로 양팔 순운동학을 동시에 연산하여 고속 포즈 반환                  |
| **`set_target(side, pose)`** | `side: str`, `pose: float32[7]`   | `None`                          | `arm_origin` site 기준 7D EE Target Pose를 해당 팔의 IK 목표로 설정           |
| **`sync(values16)`**         | `values16: float32[16]`           | `None`                          | 실제 로봇 모터에서 피드백받은 관절 각도로 IK internal `mink.Configuration`을 실시간 동기화 |
| **`solve()`**                | 없음                                | `float32[16]` \| `None`         | QP 최적화를 실행하여 양팔 16D 관절 각도(`right[8] + left[8]`) 반환 (실패 시 `None`)  |


## 5. 적용된 다중 태스크 조합 및 제약조건 메커니즘
---
`dora-openarm-kinematics-control`은 ==복수의 제어 태스크를 계층적/가중치 방식으로 조합==하여 ==실시간 안전 구동==을 보장합니다.

### 5.1 RelativeFrameTask (상대 좌표계 기준 EE 추종)
---
- `setup.origin_id`(`arm_origin` site)가 지정된 경우, 지정된 포인트의 좌표계를 기준으로 말단 손목 포즈를 추종합니다.
- 로봇 몸체의 베이스 위치가 변하더라도 오퍼레이터 상대 좌표계 기준에서 관절 각도가 일정하게 계산됩니다.

### 5.2 DofFreezingTask (미사용 관절 속도 0 고정)
---
- NANA v3 로봇의 전체 자유도 중 양팔 14축 및 그리퍼 2축을 제외한 나머지 불필요한 관절(몸통, 머리 등)의 속도를 0으로 강제 구속합니다.
- 팔 IK 연산 영향으로 인해 로봇 상체나 몸통이 기괴하게 꺾이는 현상을 물리적으로 완벽히 차단합니다.

### 5.3 PostureTask & Reach Threshold (널스페이스 자세 유도)
---
- **널스페이스(Null-space) 활용**: ==7-DOF 관절 팔은 6D 포즈를 맞추고도 1-DOF 여유 자유도==가 남습니다. 이 공간에서 주 태스크를 방해하지 않고 ==기본 홈 포즈(Mid-joint pose)를 유지하도록 유도==합니다.
- **Reach Threshold 적응**: ==말단 목표 지점과의 거리가 `0.35m`를 초과하면 posture cost를 `0.01`에서 `0.001`로 자동(Adaptive)으로 낮추어==, 자세 유지를 피하고 ==먼 거리까지 팔을 유연하게 끝까지 뻗을 수 있도록 가중치를 변환==합니다.
