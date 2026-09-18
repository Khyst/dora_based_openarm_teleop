# 5단계 양자화 핸드 제어, Frame-by-Frame 시퀀셜 스텝 제어 및 7-관절 모터 체계 통합

- **작업 일자**: 2026-09-18
- **작업 분류**: Feature / Fix / Refactor / Docs

---

## 1. 개요 및 목적
Damiao 그리퍼 모터 제거에 따른 7-관절 모터 체계 반영 과정에서 발생한 Shape Mismatch 오류, Trigger 입력 수신 조건부 포즈 게이팅 버그, 그리고 핸드 제어 시 급격한 입력 변화로 인한 모터 튐(Jerk) 현상을 최종 해결하였습니다. 

VR 컨트롤러의 Side Grip 버튼(`rg`/`lg`)은 **로봇 팔 Teleop 시작/종료 안전 클러치(Deadman Switch)** 로 동작하고, Index Trigger 버튼(`rt`/`lt`)은 **5손가락 CAN FD 로봇 손의 5단계(0%, 25%, 50%, 75%, 100%) 양자화 및 프레임 단위 시퀀셜 이동 제어**로 결합하였습니다.

---

## 2. 주요 변경 사항 및 기술 구현

### 2.1. VR 컨트롤러 버튼 역할 할당 및 5단계 양자화 (`quest_receiver.py`)
- **Side Grip 버튼 (`rg` / `lg`)**: 로봇 팔 실시간 텔레옵 활성화/비활성화 (Safety Clutch / Deadman Switch).
- **Index Trigger 버튼 (`rt` / `lt`)**: 5손가락 CAN FD 로봇 손 개폐 제어.
- **5단계 양자화 (`_discretize_trigger`)**:
  - `round(np.clip(val, 0.0, 1.0) * 4.0) / 4.0` 함수를 적용하여 아날로그 트리거 입력값을 **`0.0`, `0.25`, `0.5`, `0.75`, `1.0` 총 5단계 레벨**로 정밀 변환.
  - 포즈 배열의 8번째 요소에 직결하여 `[pose(7개), trigger_val(1개)]` 형태의 표준 8차원 벡터 출력.

### 2.2. Frame-by-Frame 시퀀셜 스텝 제어 (`hand_can.py`)
- **모터 튐(Jerk) 완전 방지**:
  - 트리거를 0%에서 100%로 갑자기 급격하게 당기더라도 단번에 100% 프레임이 송신되지 않고, 매 프레임(Tick)마다 인접 레벨(`_step_size = 25%`)씩 순차 이동 (0% $\rightarrow$ 25% $\rightarrow$ 50% $\rightarrow$ 75% $\rightarrow$ 100%).
  - CAN FD 송신 파라미터 `00C8` (200ms 속도)와 결합되어 손가락이 미끄러지듯 완만하고 부드럽게 목표 각도에 도달.
- **I/O 병목 제거**: 고주파 `print()` 호출을 `logger.debug()`로 변경하여 터미널 콘솔 I/O 병목 해소.

### 2.3. 7-관절 모터 체계 및 동기화 제어 (`main.py`, `ik.py`)
- **7-관절 동적 슬라이싱**: `_align()` 및 `_send_safe_position()`에서 `len(current_position)` (7개) 기반 동적 슬라이싱 적용으로 `ValueError: operands could not be broadcast together with shapes (7,) (6,)` 수정.
- **동기화 제어**: `dora-openarm`의 `move_position` 이벤트 루프 내에서 팔 궤적(IK)과 5손가락 CAN FD 핸드 제어 프레임을 1:1 동기화 송신.

---

## 3. 테스트 및 승인 내용
- Side Grip 버튼을 쥐었을 때만 로봇 팔이 텔레옵을 추종하고, 버튼을 떼면 대기 상태로 즉시 전환되는 Safety Clutch 동작 검증 완료.
- Index Trigger 조작 시 5단계 레벨 단위로 프레임마다 단계별 미끄러지듯 부드럽게 쥐어지는 모터 동작 검증 완료.
- 사용자의 작업 결과 최종 검토 및 승인 완료.
