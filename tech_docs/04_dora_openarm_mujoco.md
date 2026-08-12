## 1. 개요 및 모듈 목적
---
본 문서는 `nana_openarm_teleop` 시스템에서 NANA v3 로봇의 3D 물리 시뮬레이션 환경을 구축하고, 실시간 3D 뷰어 렌더링 및 디버그 오버레이, 센서 관측 데이터(Camera & Joint Observation)를 분출하는 `dora-openarm-mujoco` 노드의 기술 명세를 정리합니다.

- **실행 노드명**: `dora-openarm-mujoco`

## 2. 주요 기능 및 동작 모드 명세
---
### 2.1 주요 구동 파라미터 (CLI Options)
---

| 파라미터 인자              |   기본 설정값    |  수치 단위  | 기술적 설명 및 역할                                          |
| :------------------- | :---------: | :-----: | :--------------------------------------------------- |
| **`--scene`**        | XML/YAML 경로 |   경로    | 로봇 및 워크스페이스 셀 환경 정의 씬 모델 파일 경로                       |
| **`--viewer`**       |  `passive`  |   문자열   | 3D 뷰어 모드 (`passive` 60Hz GUI 렌더링 / `headless` 무두 구동) |
| **`--render-rate`**  |   `60.0`    |   Hz    | 3D 뷰어 화면 업데이트 및 카메라 프레임 캡처 주파수                       |
| **`--debug-frames`** |   `False`   | boolean | VR Target Pose 위치/회전 좌표축 3D 오버레이 표시 여부               |
| **`--keyframe`**     |  `"home"`   |   문자열   | X 버튼 눌림 시 씬 내 객체들을 복원시킬 MuJoCo 초기 키프레임 명칭            |

### 2.2 핵심 기능 메커니즘
---
#### 1) 실시간 3D Passive Viewer & Physics Step
---
- `mujoco.viewer.launch_passive`를 구동하여 CPU 점유를 최소화하면서 60Hz 주기 화면 업데이트.
- 수신된 `position_right`, `position_left` (관절 각도) 목표값을 MuJoCo 모터 액추에이터 포지션 입력(`ctrl`)에 즉시 반영하고 `mj_step` 구동.

#### 2) VR 디버그 프레임 오버레이 (`--debug-frames`)
---
- `pose_right`, `pose_left` 를 수신하여, 로봇의 `arm_origin` site 기점의 VR 텔레옵 목표 지점에 3D RGB 회전축 및 투명 구체(Sphere)를 디버그 오버레이 렌더링.
- 실시간으로 VR 오퍼레이터 손 궤적과 IK 연산 결과의 3D 추종 오차(Error Gap)를 눈으로 직관적 확인 가능.

#### 3) Scene Reset (X 버튼 엣지 디텍션)
---
- VR 왼손 X 버튼(`button_x`) 신호를 모니터링하여, 버튼이 눌리는 순간(Edge-triggered) 3D 씬 내의 로봇 및 사물 객체들을 저장된 `home` 키프레임 포즈로 즉시 원점 재정렬.

## 3. 데이터 처리 파이프라인 (Data Processing Pipeline)
---
### 3.1 1단계: 입력 신호 파싱 및 디코딩
---
`position_right/left` (`float32[8]`) 및 `pose_right/left` 디버그 포즈, `button_x` 리셋 신호를 수신하여 PyArrow StructArray 또는 flat numpy 배열에서 수치 디코딩.

### 3.2 2단계: MuJoCo 물리 시뮬레이션 적분 (`mj_step`)
---
- 로봇 14축 및 그리퍼 목표 각도를 `data.ctrl` 배열에 적용.
- 물리 엔진 적분 step 연산 수행 후 관절 모터 인코더/센서 피드백 수집.

### 3.3 3단계: 3D Visual Rendering & Debug Overlay
---
- `scene.add_marker`를 통해 VR Target Pose를 RGB 좌표축 마커로 오버레이.
- `viewer.sync()`를 호출하여 60Hz 화면 갱신.

### 3.4 4단계: 관측 데이터 (Observation & Camera) 출력
---
로봇 관절의 실제 수치(`arm_right_observation`)와 헤드/손목 카메라 캡처 JPEG 데이터를 하류 기록 노드(`recorder`)로 전송.

## 4. Dora 노드 입출력 인터페이스 명세 (Inputs & Outputs)
---
### 4.1 Inputs
---

| Input ID             | 데이터 형식 (Type)            | 데이터 예시 (Example)                                                  | 간단 설명 (Description)                 |
| :------------------- | :----------------------- | :---------------------------------------------------------------- | :---------------------------------- |
| **`tick`**           | `dora/timer/millis/2`    | `{"timestamp": 1723456789}`                                       | 250Hz 데이터플로우 메인 틱 신호                |
| **`position_right`** | `[{"qpos": float32[8]}]` | `[{"qpos": [0.12, -0.34, 0.05, 0.82, -0.11, 0.04, 0.02, 1.0]}]`   | `ik` 노드가 보낸 오른팔 관절 목표각              |
| **`position_left`**  | `[{"qpos": float32[8]}]` | `[{"qpos": [-0.12, -0.34, -0.05, 0.82, 0.11, 0.04, -0.02, 1.0]}]` | `ik` 노드가 보낸 왼팔 관절 목표각               |
| **`pose_right`**     | `float32[8]`             | `[0.15, 0.42, 0.98, 0.707, 0.0, 0.707, 0.0, 1.0]`                 | `--debug-frames` 시각화용 오른손 VR Target |
| **`pose_left`**      | `float32[8]`             | `[-0.15, 0.42, 0.98, 0.707, 0.0, -0.707, 0.0, 1.0]`               | `--debug-frames` 시각화용 왼손 VR Target  |
| **`button_x`**       | `uint8`                  | `1`                                                               | 3D 씬 `home` 키프레임 리셋 Trigger 버튼 신호   |
### 4.2 Outputs
---

| Output ID                   | 데이터 형식 (Type)            | 데이터 예시 (Example)                                                  | 간단 설명 (Description)         |
| :-------------------------- | :----------------------- | :---------------------------------------------------------------- | :-------------------------- |
| **`arm_right_observation`** | `[{"qpos": float32[8]}]` | `[{"qpos": [0.12, -0.34, 0.05, 0.82, -0.11, 0.04, 0.02, 1.0]}]`   | 시뮬레이션 오른팔 실제 관절 피드백 관측값     |
| **`arm_left_observation`**  | `[{"qpos": float32[8]}]` | `[{"qpos": [-0.12, -0.34, -0.05, 0.82, 0.11, 0.04, -0.02, 1.0]}]` | 시뮬레이션 왼팔 실제 관절 피드백 관측값      |
| **`camera_head_image`**     | `uint8[]`                | `JPEG binary bytes...`                                            | 헤드 위치 3D 센서 RGB 카메라 캡처 패킷   |
| **`status`**                | `string`                 | `"ready"`                                                         | MuJoCo 시뮬레이터 구동 준비 완료 상태 알림 |
