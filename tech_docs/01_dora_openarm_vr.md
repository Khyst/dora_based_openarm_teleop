
## 1. 개요 및 모듈 목적
Meta Quest 3 VR 헤드셋 및 핸드 컨트롤러의 원시(Raw) UDP 텔레메트리 패킷을 실시간 수신하여, 로봇 IK 제어에 적합한 End-Effector Target Pose 와 조작 입력으로 변환하는 `dora-openarm-vr` 노드를 정리합니다.

- **실행 노드명**: `dora-openarm-quest-receiver`
- **통신 소켓**: UDP `0.0.0.0:5006` (비동기 소켓 수신)

## 2. 수신 데이터 파싱 및 유효성(Validity) 처리 명세
### 2.1 UDP Telemetry JSON 패킷 구조

| 패킷 키 (Key)              |   데이터 타입    |     수치 범위 / 단위      | 기술적 설명                                         |
| :---------------------- | :---------: | :-----------------: | :--------------------------------------------- |
| `t`                     |    float    |     초 (Seconds)     | HMD 단조 타임스탬프 (`Time.realtimeSinceStartup`)     |
| `lc` / `rc` / `rf`      | JSON Object | `x,y,z,qx,qy,qz,qw` | 왼손 컨트롤러 / 오른손 컨트롤러 / HMD 참조 포즈 (Unity m, Quat) |
| `lt` / `rt`             |    float    |     `0.0 ~ 1.0`     | 왼손 / 오른손 인덱스 검지 트리거 (Trigger) 입력값              |
| `lg` / `rg`             |    float    |     `0.0 ~ 1.0`     | 왼손 / 오른손 중지 그립 (Grip) 입력값                      |
| `lsx, lsy` / `rsx, rsy` |    float    |    `-1.0 ~ 1.0`     | 좌/우 컨트롤러 썸스틱(Thumbstick) 2축 아날로그 입력값           |
| `a, b, x, y`            |   boolean   |   `true / false`    | Quest 핸드 컨트롤러 물리 버튼 입력 상태                      |
| `v, vl, vr`             |   integer   |      `0, 1, 2`      | HMD 전체 / 좌측 / 우측 포즈 트래킹 유효성 상태 코드              |

### 2.2 트래킹 유효성 상태(Validity) 처리 로직

| 상태 코드 (Code) | 유효성 명칭  | 처리 방식 및 시스템 동작                                             |
| :----------: | :------ | :--------------------------------------------------------- |
|     `0`      | OK      | 정상 트래킹 상태. 수신된 포즈를 좌표 변환 및 스무딩 필터에 전달하여 정상 포즈 출력.          |
|     `1`      | STALE   | 일시적 딜레이/가림 상태. HMD가 전송한 직전 정상 포즈를 보존하여 스무더를 거쳐 안전 출력.      |
|     `2`      | INVALID | 센서 트래킹 단절 상태. 포즈 출력을 중단하고, 재트래킹 시 튀김(Jump) 방지를 위해 스무더 초기화. |

> **참고**: 버튼(`a/b/x/y`), 트리거(`lt/rt`), 그립(`lg/rg`) 상태는 포즈 유효성 코드와 상관없이 항시 연속 Bypass로 전달됩니다.

<div class="page-break"></div>

## 3. 데이터 처리 파이프라인 (Data Processing Pipeline)
> 수신된 VR 컨트롤러 포즈 데이터는 다음과 같이 4단계 순차 파이프라인을 거쳐 IK 노드로 전달됩니다.

### 3.1 좌표 표현 법 변환 (Unity Left-handed $\to$ MuJoCo Right-handed)
Unity의 왼손 좌표계를 MuJoCo 오른손 좌표계로 변환합니다.
- **위치 변환 (Position Flip)**: $\mathbf{p}_{\text{mujoco}} = [x, y, -z]$
- **쿼터니언 변환 (Quat Flip)**: $\mathbf{q}_{\text{mujoco}} = [q_w, -q_x, -q_y, q_z]$

### 3.2 World 좌표계 Pose $\to$ HMD Reference 기준 Local 좌표계 Pose 변환
오퍼레이터가 Teleop를 시작한 시점의 HMD(헤드셋) 위치$(\mathbf{p}_{\text{ref}})$ 및 회전$(\mathbf{R}_{\text{ref}})$을 원점(Reference Frame)으로 삼아, **World 좌표계 포즈**를 **HMD 시점 기준의 상대(Local) 포즈로 변환**합니다.

- **상대 위치 (Local Position)**: $\mathbf{p}_{\text{rel}} = \mathbf{R}_{\text{ref}}^{-1} (\mathbf{p}_{\text{ctrl}} - \mathbf{p}_{\text{ref}})$
- **상대 회전 (Local Rotation)**: $\mathbf{R}_{\text{rel}} = \mathbf{R}_{\text{ref}}^{-1} \mathbf{R}_{\text{ctrl}}$

> **의미**: 조작자가 서 있는 위치가 달라지더라도, 영점 재설정 시 오퍼레이터의 몸 중심을 기준 원점으로 포즈를 재정렬하여 작업 편의성 및 안전성을 확보합니다.

### 3.3 3단계: One Euro Filter 적응형 스무딩
HMD Local 좌표계로 변환된 포즈 신호의 **미세 떨림**과 **고주파 노이즈**를 속도 감응형 적응 기술인 **One Euro Filter**로 필터링합니다.

| 필터 파라미터          |  기본 설정값  | 역할 및 체감 영향                                   |
| :--------------- | :------: | :------------------------------------------- |
| **`min_cutoff`** | `1.0 Hz` | 저속 정지 상태에서의 최소 차단 주파수 (미세 떨림 및 지터링 완전 제거)    |
| **`beta`**       | `0.005`  | 속도 감응 계수 (손을 빠르게 움직일 때 차단 주파수를 높여 반응 지연 최소화) |
| **`d_cutoff`**   | `1.0 Hz` | 미분(속도) 신호 필터링을 위한 차단 주파수                     |

### 3.4 4단계: 로봇 작업 공간 매핑 (Workspace Mapping)
**사람의 가슴 높이**에서의 **End-effector의 상대 포즈**를 **NANA v3 로봇**의 **`arm_origin` site(가슴 높이) 원점 좌표계**로 변환 및 90도 회전 정렬($\mathbf{R}_{\text{fix}}$)을 적용합니다.
- $\mathbf{p}_{\text{out}} = \mathbf{R}_{\text{frame}} \cdot \mathbf{p}_{\text{rel}} + \mathbf{p}_{\text{arm\_origin}}$
- $\mathbf{R}_{\text{out}} = \mathbf{R}_{\text{frame}} \cdot \mathbf{R}_{\text{rel}} \cdot \mathbf{R}_{\text{fix}}$ ($\mathbf{R}_{\text{fix}} = \text{Rot}_z(90^\circ)$)

<div class="page-break"></div>


## 4. Dora 노드 입출력 인터페이스 명세 (Inputs & Outputs)
### 4.1 Inputs

| Input ID   | 데이터 형식 (Type)         | 데이터 예시 (Example)            | 간단 설명 (Description)                                     |
| :--------- | :-------------------- | :-------------------------- | :------------------------------------------------------ |
| **`tick`** | `dora/timer/millis/2` | `{"timestamp": 1723456789}` | `quittable-tick-leader` 노드로부터 전달받는 250Hz 주기 데이터플로우 틱 신호 |

### 4.2 Outputs

| Output ID              | 데이터 형식 (Type) | 데이터 예시 (Example)                                    | 간단 설명 (Description)                                                  |
| :--------------------- | :------------ | :-------------------------------------------------- | :------------------------------------------------------------------- |
| **`pose_right`**       | `float32[8]`  | `[0.15, 0.42, 0.98, 0.707, 0.0, 0.707, 0.0, 0.0]`   | 오른손 EE 타겟 포즈 `[px,py,pz,qw,qx,qy,qz]` 및 그립값(`grip`) $\to$ `ik` 노드 전달 |
| **`pose_left`**        | `float32[8]`  | `[-0.15, 0.42, 0.98, 0.707, 0.0, -0.707, 0.0, 0.0]` | 왼손 EE 타겟 포즈 `[px,py,pz,qw,qx,qy,qz]` 및 그립값(`grip`) $\to$ `ik` 노드 전달  |
| **`trigger_right`**    | `float32`     | `0.85`                                              | 오른손 검지 인덱스 트리거 아날로그 입력값 (`0.0 ~ 1.0`)                                |
| **`trigger_left`**     | `float32`     | `0.0`                                               | 왼손 검지 인덱스 트리거 아날로그 입력값 (`0.0 ~ 1.0`)                                 |
| **`grip_right`**       | `float32`     | `1.0`                                               | 오른손 중지 그립 아날로그 입력값 (`0.0 ~ 1.0`)                                     |
| **`grip_left`**        | `float32`     | `0.0`                                               | 왼손 중지 그립 아날로그 입력값 (`0.0 ~ 1.0`)                                      |
| **`joystick_x_right`** | `float32`     | `0.0`                                               | 오른손 썸스틱 X축 입력값 (`-1.0 ~ 1.0`)                                        |
| **`joystick_y_right`** | `float32`     | `0.5`                                               | 오른손 썸스틱 Y축 입력값 (`-1.0 ~ 1.0`)                                        |
| **`button_a`**         | `uint8`       | `1`                                                 | 오른손 A 버튼 눌림 상태 (`1`=Pressed, `0`=Released)                           |
| **`button_b`**         | `uint8`       | `0`                                                 | 오른손 B 버튼 눌림 상태 (`1`=Pressed, `0`=Released)                           |
| **`button_x`**         | `uint8`       | `0`                                                 | 왼손 X 버튼 눌림 상태 (`1`=Pressed, `0`=Released)                            |
| **`button_y`**         | `uint8`       | `0`                                                 | 왼손 Y 버튼 눌림 상태 (`1`=Pressed, `0`=Released)                            |
| **`status`**           | `string`      | `"ready"`                                           | 노드 정상 초기화 및 수신 구동 알림 신호                                              |
