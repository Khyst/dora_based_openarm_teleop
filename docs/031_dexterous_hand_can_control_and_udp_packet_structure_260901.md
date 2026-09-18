# VR 트리거 기반 핸드 CAN FD 제어 구현 및 Meta Quest UDP 패킷 데이터 구조 명세

- **작업 일자**: 2026-09-18
- **작업 분류**: Feature / Fix / Docs

---

## 1. 개요 및 목적
Meta Quest VR 컨트롤러의 `trigger_right`, `trigger_left` 입력(검지 트리거 눌림 정도: 0.0 ~ 1.0)을 Dora 데이터플로우를 통해 수신하고, 오른쪽 덱스트러스 5핑거 핸드를 SocketCAN (`can0` 인터페이스, CAN FD) 통신을 사용하여 실시간으로 제어하도록 구현하였습니다. 또한, 로봇 구동 시 순간적인 목표 위치 급변으로 인한 드라이버 다운 현상을 안전하게 방지하고, Meta Quest 3 기기로부터 수신되는 UDP JSON 데이터 구조를 명확히 문서화합니다.

---

## 2. 주요 변경 사항 및 기술 구현

### 2.1. 덱스트러스 핸드 CAN FD 제어 모듈 (`hand_can.py`)
- **SocketCAN RAW FD 통신**: Python native `socket.AF_CAN` 소켓을 활용하여 CAN FD 패킷(ID: `0x008`, `CANFD_BRS` 플래그) 전송.
- **손가락 굴곡 매핑**:
  - `trigger_val` [0.0, 1.0] $\rightarrow$ 손가락 각도 0 ~ 100% (`0x00` ~ `0x64`) 선형 매핑.
  - CAN FD 페이로드 구조: `00 32 32 32 32 32` (헤더 6B) + `[val] * 5` (손가락 5B) + `03 E8` (테일 2B).
  - 예시 command: `cansend can0 008##1003232323232646464646403E8`
- **실시간 모니터링**: 트리거 상태 변경 시 터미널 콘솔에 `[HandCanController] Trigger: 0.50 (50%) -> Sent: cansend ...` 형태의 명확한 송신 로그 출력.

### 2.2. 로봇 드라이버 및 데이터플로우 안전 보완 (`main.py`, `quest_receiver.py`)
- **안전 속도 클램핑 (`_send_safe_position`)**:
  - 텔레옵 급변이나 그립 재진입 시 관절 이동량(Delta)이 하드웨어 한계치(`joint_delta_position_limits`, 그리퍼 0.4 rad/step)를 초과하여 발생하던 `RuntimeError` 원천 차단.
  - 차이값(`diff`)을 `[-delta_limits, delta_limits]` 내로 자동으로 안전하게 제한(Clip)하여 추종.
- **PyArrow 스칼라 타입 변환 (`_to_float_scalar`)**:
  - PyArrow `FloatArray`에서 안전하게 단일 `float` 스칼라 값을 추출하는 헬퍼 함수 구현.
- **입력 채널 독립 분리**:
  - 검지 트리거 (`rt`/`lt`) $\rightarrow$ 5핑거 덱스트러스 핸드 CAN 제어 독립 할당.
  - 측면 그립 버튼 (`rg`/`lg`) $\rightarrow$ Arm 1-DOF 그리퍼 각도 및 어깨/팔 텔레옵 활성화 상태에 할당.

---

## 3. Meta Quest UDP 수신 패킷 JSON 데이터 구조 (`_parse_packet`)

`udp_receiver.py` 내 `_parse_packet(data)` 함수는 Meta Quest 3 전송 앱으로부터 수신된 바이트(`bytes`) 데이터를 UTF-8 디코딩 및 `json.loads(line)`하여 파이썬 사전(`dict`) 데이터 구조(`parsed`)로 변환합니다.

### 3.1. parsed 데이터 구조 상세 (JSON Schema)

| 키 (Key)　　　| 데이터 타입 | 설명 및 유효 범위　　　　　　　　　　　　　　　　　　　　　　　　　　　　 | 　　　　　　　　　　　　　　　　　　　　　　　　　 |
| :--------------| :------------| :--------------------------------------------------------------------------| ----------------------------------------------------|
| `t`　　　　　 | `float`　　 | Quest 헤드셋 단조 시간 타임스탬프 (초, Unity `Time.realtimeSinceStartup`) | 　　　　　　　　　　　　　　　　　　　　　　　　　 |
| `v`　　　　　 | `int`　　　 | 전체 포즈 추적 유효성 (0: `OK`, 1: `STALE`, 2: `INVALID`)　　　　　　　　 | 　　　　　　　　　　　　　　　　　　　　　　　　　 |
| `vl`　　　　　| `int`　　　 | 왼손 컨트롤러 추적 유효성 (0: `OK`, 1: `STALE`, 2: `INVALID`)　　　　　　 | 　　　　　　　　　　　　　　　　　　　　　　　　　 |
| `vr`　　　　　| `int`　　　 | 오른손 컨트롤러 추적 유효성 (0: `OK`, 1: `STALE`, 2: `INVALID`)　　　　　 | 　　　　　　　　　　　　　　　　　　　　　　　　　 |
| `rf`　　　　　| `dict` \　　| `null`　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　| 헤드셋(HMD) 3D 포즈 데이터 (Unity 왼손 좌표계)　　 |
| `rc`　　　　　| `dict` \　　| `null`　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　| 오른손 컨트롤러 3D 포즈 데이터 (Unity 왼손 좌표계) |
| `lc`　　　　　| `dict` \　　| `null`　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　| 왼손 컨트롤러 3D 포즈 데이터 (Unity 왼손 좌표계)　 |
| `rt`　　　　　| `float`　　 | 오른쪽 검지 트리거 (Right Index Trigger) 눌림 비율 (`0.0` ~ `1.0`)　　　　| 　　　　　　　　　　　　　　　　　　　　　　　　　 |
| `lt`　　　　　| `float`　　 | 왼쪽 검지 트리거 (Left Index Trigger) 눌림 비율 (`0.0` ~ `1.0`)　　　　　 | 　　　　　　　　　　　　　　　　　　　　　　　　　 |
| `rg`　　　　　| `float`　　 | 오른쪽 측면 그립 버튼 (Right Grip Button) 눌림 비율 (`0.0` ~ `1.0`)　　　 | 　　　　　　　　　　　　　　　　　　　　　　　　　 |
| `lg`　　　　　| `float`　　 | 왼쪽 측면 그립 버튼 (Left Grip Button) 눌림 비율 (`0.0` ~ `1.0`)　　　　　| 　　　　　　　　　　　　　　　　　　　　　　　　　 |
| `rsx` / `rsy` | `float`　　 | 오른쪽 썸스틱 (Thumbstick) X / Y 축 입력 값 (`-1.0` ~ `+1.0`)　　　　　　 | 　　　　　　　　　　　　　　　　　　　　　　　　　 |
| `lsx` / `lsy` | `float`　　 | 왼쪽 썸스틱 (Thumbstick) X / Y 축 입력 값 (`-1.0` ~ `+1.0`)　　　　　　　 | 　　　　　　　　　　　　　　　　　　　　　　　　　 |
| `a` / `b`　　 | `bool`　　　| 오른쪽 컨트롤러 A / B 버튼 눌림 상태 (`true` / `false`)　　　　　　　　　 | 　　　　　　　　　　　　　　　　　　　　　　　　　 |
| `x` / `y`　　 | `bool`　　　| 왼쪽 컨트롤러 X / Y 버튼 눌림 상태 (`true` / `false`)　　　　　　　　　　 | 　　　　　　　　　　　　　　　　　　　　　　　　　 |

#### 포즈 객체(`rf`, `rc`, `lc`) 내부 하위 구조:
- `x`, `y`, `z` (`float`): Unity 왼손 좌표계 기준 3차원 위치 좌표 (단위: 미터)
- `qx`, `qy`, `qz`, `qw` (`float`): Unity 왼손 좌표계 기준 회전 쿼터니언 (Quaternion)

### 3.2. parsed JSON 예시 데이터

```json
{
  "t": 1045.382,
  "v": 0,
  "vl": 0,
  "vr": 0,
  "rf": {
    "x": 0.012,
    "y": 1.650,
    "z": 0.150,
    "qx": 0.000,
    "qy": 0.000,
    "qz": 0.000,
    "qw": 1.000
  },
  "rc": {
    "x": 0.235,
    "y": 1.420,
    "z": 0.480,
    "qx": 0.102,
    "qy": 0.198,
    "qz": 0.015,
    "qw": 0.975
  },
  "lc": {
    "x": -0.235,
    "y": 1.420,
    "z": 0.480,
    "qx": 0.102,
    "qy": -0.198,
    "qz": -0.015,
    "qw": 0.975
  },
  "rt": 0.75,
  "lt": 0.00,
  "rg": 1.00,
  "lg": 0.00,
  "rsx": 0.00,
  "rsy": 0.00,
  "lsx": 0.00,
  "lsy": 0.00,
  "a": false,
  "b": false,
  "x": false,
  "y": false
}
```

---

## 4. 테스트 및 승인 내용
- `HandCanController` 단독 CAN FD 패킷 생성 및 전송 기능 검증 완료.
- `_to_float_scalar` 파이프라인 및 `_send_safe_position` 안전 클램핑 적용 후 구문/타입 검증 완료.
- 사용자 최종 승인 완료.
