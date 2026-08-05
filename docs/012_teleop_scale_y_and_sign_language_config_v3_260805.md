# 012. VR 텔레옵 좌우 감도 보정 및 수화 맞춤 셀 설정 (`nana_v3_cell_v3.yaml`) 정리 (2026-08-05)

## 📌 개요

본 문서는 NANA v3 로봇의 VR 텔레오퍼레이션(Teleoperation) 및 수화 표현 동작 실험 중 발생한 **어깨 Yaw 꺾임 현상**과 **팔 벌림 감도 보정**, 그리고 **하드웨어 진단 툴 가이드**를 통합 정돈하고, 수화 동작 표현성과 하드웨어 안전성을 고려하여 새롭게 작성된 드라이버 설정 파일(`nana_v3_cell_v3.yaml`)에 대한 변경 내역을 기록합니다.

---

## 1. VR 텔레옵 좌우 팔 벌림 감도 조정 (`--scale-y`)

- **배경**: 조종자의 팔 위치 대비 로봇 팔이 몸 안쪽으로 치우치는 현상을 보정하기 위해 좌우 스트레치 스케일 인자 조정.
- **적용 파일**: [`src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop.yaml`](file:///home/khy/2.dora_based_openarm_teleop/src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop.yaml)
- **변경 사항**:
  ```yaml
  - id: udp-receiver
    build: pip install -e ..
    path: dora-openarm-quest-receiver
    args: "--host 0.0.0.0 --port 5006 --scale-x 1.0 --scale-y 1.15 --scale-z 1.0"
  ```
- **효과**: VR 컨트롤러의 Y축(좌우) 움직임에 1.15배 스케일 가인을 적용하여 조종 시 팔이 몸 바깥쪽으로 더 자연스럽게 뻗어 나가도록 유도.

---

## 2. README.md 내 하드웨어 진단 도구 가이드 추가 (`openarm-can-cli`)

- **적용 파일**: [`README.md`](file:///home/khy/2.dora_based_openarm_teleop/README.md)
- **추가 내용**:
  - `can0` (오른팔), `can1` (왼팔) 모터 실시간 상태 모니터링 (`monitor`)
  - CAN 버스 연결 모터 스캔 (`discover`)
  - 모터 토크 ON/OFF (`enable`, `disable`)
  - 모터 에러 클리어 (`clear_error`) 및 PID/Limit 파라미터 조회 (`show_param`)

---

## 3. 어깨 Yaw 급격한 회전 완화 및 셀 설정 파일 (`nana_v3_cell_v3.yaml`) 작성

- **배경**: 텔레옵 시 어깨 Yaw(Joint 2) 관절이 순간적으로 획 돌아가 부자연스러운 기괴한 자세(Singularity 근처)를 취하는 문제 방지.
- **적용 파일**:
  - [`src/nana_v3_dora_teleop_vr/openarm_driver/src/openarm_driver/configs/nana_v3_cell_v2.yaml`](file:///home/khy/2.dora_based_openarm_teleop/src/nana_v3_dora_teleop_vr/openarm_driver/src/openarm_driver/configs/nana_v3_cell_v2.yaml) (Delta Limit 0.8 -> 0.3 rad/s)
  - [`src/nana_v3_dora_teleop_vr/openarm_driver/src/openarm_driver/configs/nana_v3_cell_v3.yaml`](file:///home/khy/2.dora_based_openarm_teleop/src/nana_v3_dora_teleop_vr/openarm_driver/src/openarm_driver/configs/nana_v3_cell_v3.yaml) (신규 생성)

### 수화 맞춤 조인트 가동 범위 (`joint_limits`) 설정 요약

| 관절 | 명칭 | 기존 범위 | **nana_v3_cell_v3.yaml 범위** | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| **J0** | Shoulder Pitch | $-80^\circ \sim +200^\circ$ | **$-45^\circ \sim +150^\circ$** (`[-0.785398, 2.617994]`) | 차렷부터 머리 위 표현 허용, 등 뒤 꼬임 방지 |
| **J1** | Shoulder Roll | $-100^\circ \sim +100^\circ$ | **$-60^\circ \sim +90^\circ$** (`[-1.047198, 1.570796]`) | 몸 안쪽 간섭 방지 및 팔 벌림 공간 표현 |
| **J2** | **Shoulder Yaw** | $-90^\circ \sim +90^\circ$ | **$-60^\circ \sim +60^\circ$** (`[-1.047198, 1.047198]`) | **수화 트위스트 보장 & 어깨 꺾임 완벽 예방** |
| **J3** | Elbow Pitch | $0^\circ \sim +140^\circ$ | **$0^\circ \sim +135^\circ$** (`[0.0, 2.356194]`) | 턱/가슴 가리키는 팔꿈치 접힘 보장 |
| **J4** | Wrist Roll | $-90^\circ \sim +90^\circ$ | **$-90^\circ \sim +90^\circ$** (`[-1.570796, 1.570796]`) | 손바닥 위/아래 방향성 표현 |
| **J5** | Wrist Pitch | $-45^\circ \sim +45^\circ$ | **$-45^\circ \sim +45^\circ$** (`[-0.785398, 0.785398]`) | **Official 하드웨어 스펙 및 Hard Stop 준수** |
| **J6** | Wrist Yaw | $-90^\circ \sim +90^\circ$ | **$-90^\circ \sim +90^\circ$** (`[-1.570796, 1.570796]`) | 손끝 방향(Direction) 표현 유지 |

---

## 4. 결론 및 향후 적용법

새롭게 생성된 `nana_v3_cell_v3.yaml`은 수화 동작 표현성과 로봇 하드웨어의 안전성을 동시에 만족하도록 설계되었습니다.
실물 로봇 제어 시 dataflow YAML 설정에서 다음과 같이 config를 변경하여 실행할 수 있습니다:

```yaml
args: "--side right --align-trigger gripper --config ../../openarm_driver/src/openarm_driver/configs/nana_v3_cell_v3.yaml"
```
