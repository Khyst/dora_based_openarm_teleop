# Dora OpenArm Follower Driver & Safety Parameters Guide

- **작업 일자**: 2026-07-30
- **작업 분류**: Docs

## 1. 개요 및 목적
본 문서는 `dora-openarm` (로봇 팔 하드웨어 Follower 드라이버 노드)이 IK 계산을 통해 도출된 관절 각도(`qpos`)를 수신하여 CAN 통신 기반 실물 모터를 안전하게 제어하는 과정에서 사용되는 **안전 정렬(Safety Alignment) 기능**과 **핵심 파라미터 조절 가이드**를 정리하는 것을 목적으로 합니다.

---

## 2. 하드웨어 제어 파이프라인 (Control Pipeline)

```
[IK Node] ➔ (qpos: Joint Angles) ➔ [dora-openarm Node] ➔ (CAN Bus) ➔ [OpenARM Motors]
                                              └─ ➔ (state: Telmetry) ➔ [Recorder / UI]
```

* **입력 데이터**: `move_position` / `request_state` (관절 각도 8D/16D `qpos` 배열)
* **출력 데이터**:
  * `status`: 현재 팔 상태 (`stopped`, `started`, `aligned`)
  * `state`: CAN 통신 기반 모터 텔레메트리 (위치, 속도, 토크, FET/로터 온도 등)

---

## 3. 핵심 안전 기능: 안전 정렬 (Safety Alignment)

### 3.1 필요성
VR 텔레오퍼레이션을 시작하거나 끊겼다 연결될 때, **"실물 로봇 팔의 현재 관절 위치"**와 **"VR에서 들어온 첫 번째 목표 관절 위치"** 사이에 큰 차이가 존재할 수 있습니다. 
아무런 안전 대책 없이 목표 위치를 모터에 즉시 명령하면 로봇 팔이 채찍처럼 튀면서 주변 물체나 사람과 충돌할 수 있습니다.

### 3.2 안전 정렬 단계별 동작 원리 (`_align` 함수)

1. **단계적 점진 이동 (Step Limit)**:
   - 목표 위치와 현재 실물 위치의 차이(Diff)를 계산하고, 한 스텝 당 최대 `--align-delta-limit` (예: `0.001 rad/step`) 이내로 제한하여 부드럽게 목표 위치로 끌고옵니다.
2. **정렬 완료 검증 (Threshold Check)**:
   - 실물 관절과 목표 관절 간의 오차가 `--align-threshold` (예: `0.1 rad`) 이하로 좁혀지면 비로소 **`ALIGNED` 상태**로 승격되어 실시간 $1:1$ 손동작 추종으로 전환됩니다.
3. **그리퍼 트리거 제어 (`--align-trigger gripper`)**:
   - 작업자가 VR 컨트롤러의 그립(Grip)을 잡고 있는 상태(`is_gripping`)에서만 정렬 동작이 유효하게 발동하도록 물리적 스위치 안전장치를 제공합니다.

---

## 4. 핵심 파라미터 및 사용자 튜닝 가이드

### 4.1 파라미터 요약 표

| 파라미터 | 기본값 | 주요 역할 | 튜닝 시 가이드 및 효과 |
| :--- | :--- | :--- | :--- |
| **`--side`** | `right` | 제어할 로봇 팔 지정 | `right` (오른팔), `left` (왼팔) 중 선택. |
| **`--align-delta-limit`** | `0.001` | **정렬 모드 최대 이동 속도** | 🌟 **핵심 안전 파라미터**<br>• 값을 **낮추면** (예: `0.0002 ~ 0.0005`): 정렬 시 로봇 팔이 더욱 천천히 부드럽게 이동하여 안전합니다.<br>• 값을 **높이면** (예: `0.002`): 정렬 도달 속도가 빨라지나 튈 위험이 생깁니다. |
| **`--align-threshold`** | `0.1` | **정렬 완료 오차 임계값 (rad)** | • 실물 관절과 목표 관절의 오차가 이 값 미만이어야 실시간 조종(`ALIGNED`)으로 전환됩니다.<br>• 일반적으로 `0.1 rad` (~5.7도) 유지를 권장합니다. |
| **`--align-trigger`** | `None` | **정렬 발동 스위치 조건** | • `gripper`로 설정 시 VR 컨트롤러 그립을 쥐고 있는 동안에만 정렬 및 조종이 동작합니다. |
| **`--align`** | `True` | 안전 정렬 기능 사용 여부 | • `True` (기본값, 사용 권장): 초기 정렬 과정을 거침.<br>• `False`: 정렬 과정 없이 목표 위치로 즉시 전송 (위험할 수 있음). |
| **`--start-on-startup`** | `False` | 노드 실행 시 즉시 모터 켜기 | • `True` 설정 시 노드 시작과 동시에 CAN 모터 통신 및 드라이버 활성화. |
| **`--stop`** | `True` | 노드 종료 시 모터 정지 | • `True` (기본값): 노드가 꺼질 때 모터 출력을 안전하게 차단하고 정지시킴. |
| **`--refresh-every-request`** | `True` | 정밀도 향상을 위한 모터 갱신 | • 매 입력 요청마다 하드웨어 상태를 갱신하여 정밀도를 극대화합니다. |

---

## 5. 실시간 하드웨어 텔레메트리 피드백 (`state`)

`dora-openarm`은 모터에 명령을 전달함과 동시에, CAN 버스로부터 모터의 물리적 상태를 실시간 수집하여 Dora 채널로 출력합니다.

* **`qpos`**: 모터 엔코더 기반 실제 관절 위치 (8D `float32`)
* **`qvel`**: 관절 회전 속도 (8D `float32`)
* **`qtorque`**: 현재 모터 인가 토크 (과부하 및 잼 현상 감지)
* **`tmos`**: **FET 모터 드라이버 기판 온도 (℃)** ➔ 모터 드라이버 과열 방지
* **`trotor`**: **모터 로터 내부 온도 (℃)** ➔ 모터 코일 탄화/오버히트 방지

---

## 6. 실제 Dataflow YAML 설정 예시

```yaml
  - id: follower-right
    build: pip install -e ../../dora-openarm
    path: dora-openarm
    args: "--side right --align-trigger gripper --align-delta-limit 0.0002 --start-on-startup --config .../configs/nana_v3_cell.yaml"
    inputs:
      request_state: ik/position_right
      move_position: ik/position_right
      grip: udp-receiver/grip_right
    outputs:
      - state
      - status
```

---

## 7. 테스트 및 승인 내용
- **검증 방식**: `dora-openarm` 내 `main.py` 소스 코드 및 `SingleArmDriver` 안전 로직 분석 완료.
- **결과**: Safety Alignment 작동 메커니즘, 8대 핵심 조절 파라미터 가이드, CAN 하드웨어 텔레메트리 구조 정리 문서 작성 완료.
