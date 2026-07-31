# NANA v3 URDF 로봇 관절(Joint) 명세 및 가동 범위(Limit) 가이드

- **작업 일자**: 2026-07-31
- **작업 분류**: Docs

## 1. 개요 및 목적
- 보정 반영된 NANA v3 로봇 모델(`nana_v3_corrected.urdf`)에 정의된 총 19개 관절(Joint)의 상세 프로퍼티, 마운팅 오프셋, 회전축(Axis), 및 가동 범위 제한(Limit: Lower, Upper, Effort, Velocity)을 체계적으로 정리함.
- 텔레옵(VR Teleoperation) IK 역운동학 제어, 하드웨어 안전 가동 영역(Safety Boundary) 설정, 및 MuJoCo 시뮬레이션 환경의 기준 문서로 활용함.

## 2. 관절 명세 및 속성 (Joint Specifications)

### 2.1 관절 구성 개요
- **총 관절 수**: 19개
  - **고정 관절 (Fixed Joint)**: 5개 (`world` 연동 1개, 몸체-어깨 연동 2개, 엔드이펙터 핸드 2개)
  - **회전 관절 (Revolute Joint)**: 14개 (왼팔 7-DOF, 오른팔 7-DOF)

---

### 2.2 7축 회전 관절 (Revolute Joints, 총 14개)

#### 1) 왼팔 관절 (Left Arm: 7-DOF)
| 관절명 (Joint Name)　　　 | 타입　　 | Parent $\to$ Child              | 회전축 (Axis) | 가동 범위 (Lower ~ Upper)　　　　　　　　　　　　　　　　　　　　　 | 최대 토크 (Effort)　　　　　| 최대 속도 (Velocity)　　　　　　　　　　　　　|
| :--------------------------| :--------:| :-------------------------------:| :-------------:| :-------------------------------------------------------------------:| :---------------------------:| :---------------------------------------------:|
| **`nana_v3_left_joint1`** | revolute | `left_link0` $\to$ `left_link1` | `(0, 0, 1)`　 | $-1.3963 \sim 3.4907 \text{ rad}$<br>($-80^\circ \sim +200^\circ$)　| $40 \text{ N}\cdot\text{m}$ | $16.75 \text{ rad/s}$ ($960^\circ/\text{s}$)　|
| **`nana_v3_left_joint2`** | revolute | `left_link1` $\to$ `left_link2` | `(-1, 0, 0)`　| $-1.7453 \sim 1.7453 \text{ rad}$<br>($-100^\circ \sim +100^\circ$) | $40 \text{ N}\cdot\text{m}$ | $16.75 \text{ rad/s}$ ($960^\circ/\text{s}$)　|
| **`nana_v3_left_joint3`** | revolute | `left_link2` $\to$ `left_link3` | `(0, 0, 1)`　 | $-1.5708 \sim 1.5708 \text{ rad}$<br>($-90^\circ \sim +90^\circ$)　 | $27 \text{ N}\cdot\text{m}$ | $5.45 \text{ rad/s}$ ($312^\circ/\text{s}$)　 |
| **`nana_v3_left_joint4`** | revolute | `left_link3` $\to$ `left_link4` | `(0, 1, 0)`　 | $0.0 \sim 2.4435 \text{ rad}$<br>($0^\circ \sim +140^\circ$)　　　　| $27 \text{ N}\cdot\text{m}$ | $5.45 \text{ rad/s}$ ($312^\circ/\text{s}$)　 |
| **`nana_v3_left_joint5`** | revolute | `left_link4` $\to$ `left_link5` | `(0, 0, 1)`　 | $-1.5708 \sim 1.5708 \text{ rad}$<br>($-90^\circ \sim +90^\circ$)　 | $7 \text{ N}\cdot\text{m}$　| $20.94 \text{ rad/s}$ ($1200^\circ/\text{s}$) |
| **`nana_v3_left_joint6`** | revolute | `left_link5` $\to$ `left_link6` | `(1, 0, 0)`　 | $-0.7854 \sim 0.7854 \text{ rad}$<br>($-45^\circ \sim +45^\circ$)　 | $7 \text{ N}\cdot\text{m}$　| $20.94 \text{ rad/s}$ ($1200^\circ/\text{s}$) |
| **`nana_v3_left_joint7`** | revolute | `left_link6` $\to$ `left_link7` | `(0, -1, 0)`　| $-1.5708 \sim 1.5708 \text{ rad}$<br>($-90^\circ \sim +90^\circ$)　 | $7 \text{ N}\cdot\text{m}$　| $20.94 \text{ rad/s}$ ($1200^\circ/\text{s}$) |

#### 2) 오른팔 관절 (Right Arm: 7-DOF)
| 관절명 (Joint Name) | 타입 | Parent $\to$ Child | 회전축 (Axis) | 가동 범위 (Lower ~ Upper) | 최대 토크 (Effort) | 최대 속도 (Velocity) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`nana_v3_right_joint1`** | revolute | `right_link0` $\to$ `right_link1` | `(0, 0, 1)` | $-1.3963 \sim 3.4907 \text{ rad}$<br>($-80^\circ \sim +200^\circ$) | $40 \text{ N}\cdot\text{m}$ | $16.75 \text{ rad/s}$ ($960^\circ/\text{s}$) |
| **`nana_v3_right_joint2`** | revolute | `right_link1` $\to$ `right_link2` | `(-1, 0, 0)` | $-1.7453 \sim 1.7453 \text{ rad}$<br>($-100^\circ \sim +100^\circ$) | $40 \text{ N}\cdot\text{m}$ | $16.75 \text{ rad/s}$ ($960^\circ/\text{s}$) |
| **`nana_v3_right_joint3`** | revolute | `right_link2` $\to$ `right_link3` | `(0, 0, 1)` | $-1.5708 \sim 1.5708 \text{ rad}$<br>($-90^\circ \sim +90^\circ$) | $27 \text{ N}\cdot\text{m}$ | $5.45 \text{ rad/s}$ ($312^\circ/\text{s}$) |
| **`nana_v3_right_joint4`** | revolute | `right_link3` $\to$ `right_link4` | `(0, 1, 0)` | $0.0 \sim 2.4435 \text{ rad}$<br>($0^\circ \sim +140^\circ$) | $27 \text{ N}\cdot\text{m}$ | $5.45 \text{ rad/s}$ ($312^\circ/\text{s}$) |
| **`nana_v3_right_joint5`** | revolute | `right_link4` $\to$ `right_link5` | `(0, 0, 1)` | $-1.5708 \sim 1.5708 \text{ rad}$<br>($-90^\circ \sim +90^\circ$) | $7 \text{ N}\cdot\text{m}$ | $20.94 \text{ rad/s}$ ($1200^\circ/\text{s}$) |
| **`nana_v3_right_joint6`** | revolute | `right_link5` $\to$ `right_link6` | `(1, 0, 0)` | $-0.7854 \sim 0.7854 \text{ rad}$<br>($-45^\circ \sim +45^\circ$) | $7 \text{ N}\cdot\text{m}$ | $20.94 \text{ rad/s}$ ($1200^\circ/\text{s}$) |
| **`nana_v3_right_joint7`** | revolute | `right_link6` $\to$ `right_link7` | `(0, 1, 0)` | $-1.5708 \sim 1.5708 \text{ rad}$<br>($-90^\circ \sim +90^\circ$) | $7 \text{ N}\cdot\text{m}$ | $20.94 \text{ rad/s}$ ($1200^\circ/\text{s}$) |

---

### 2.3 고정 관절 (Fixed Joints, 총 5개)

| 관절명 (Joint Name) | 타입 | Parent $\to$ Child | 위치 오프셋 (`xyz`) | 회전 오프셋 (`rpy`) |
| :--- | :---: | :---: | :---: | :---: |
| **`nana_v3_body_world_joint`** | fixed | `world` $\to$ `nana_v3_body_link0` | `xyz="0 0 0"` | `rpy="0 0 0"` |
| **`nana_v3_left_nana_v3_body_link0_joint`** | fixed | `body_link0` $\to$ `left_link0` | `xyz="0.0 0.18 1.22"` | `rpy="-1.5708 0 0"` ($-90^\circ$ X축 회전) |
| **`nana_v3_right_nana_v3_body_link0_joint`** | fixed | `body_link0` $\to$ `right_link0` | `xyz="0.0 -0.18 1.22"` | `rpy="1.5708 0 0"` ($+90^\circ$ X축 회전) |
| **`nana_v3_left_hand_joint`** | fixed | `left_link7` $\to$ `left_hand` | `xyz="0 0 0.08"` | `rpy="0 0 0"` |
| **`nana_v3_right_hand_joint`** | fixed | `right_link7` $\to$ `right_hand` | `xyz="0 0 0.08"` | `rpy="0 0 0"` |

---

### 2.4 관절별 로컬 좌표계 오프셋 (Joint Local Origin)

- **`left_joint1` / `right_joint1`**: `xyz="0.0 0.0 0.0625"`, `rpy="0 0 0"`
- **`left_joint2`**: `xyz="-0.0301 0.0 0.06"`, `rpy="-1.57079632679 0 0"`
- **`right_joint2`**: `xyz="-0.0301 0.0 0.06"`, `rpy="1.57079632679 0 0"`
- **`left_joint3` / `right_joint3`**: `xyz="0.0301 0.0 0.06625"`, `rpy="0 0 0"`
- **`left_joint4` / `right_joint4`**: `xyz="-0.0 0.0315 0.15375"`, `rpy="0 0 0"`
- **`left_joint5` / `right_joint5`**: `xyz="0.0 -0.0315 0.0955"`, `rpy="0 0 0"`
- **`left_joint6` / `right_joint6`**: `xyz="0.0375 0.0 0.1205"`, `rpy="0 0 0"`
- **`left_joint7` / `right_joint7`**: `xyz="-0.0375 0.0 0.0"`, `rpy="0 0 0"`

---

## 3. 테스트 및 승인 내용
- URDF XML 파싱 검증 완료 (`openarm` 로봇 조인트 무결성 확인).
- 사용자 검토 및 최종 문서 작성 승인 완료.
