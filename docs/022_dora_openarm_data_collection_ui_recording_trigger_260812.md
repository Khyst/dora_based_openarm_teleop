# dora-openarm-data-collection-ui 레코딩 트리거 연동 및 Dataflow UI/Recorder 추가

- **작업 일자**: 2026-08-11
- **작업 분류**: Feature / Refactor

## 1. 개요 및 목적
- `run_sim.sh` 및 `run_real.sh` 실행 환경에서 웹 UI(http://localhost:8000)를 통해 데이터 레코딩을 손쉽게 제어하고, VR 컨트롤러의 트리거 버튼을 눌러 로봇이 Teleop으로 움직이는 상태를 실시간 시각화하며 데이터셋을 레코드할 수 있도록 `dora-openarm-data-collection-ui` 및 dataflow yaml 구성을 수정함.

## 2. 주요 변경 사항
- **UI 백엔드 (`dora-openarm-data-collection-ui/src/dora_openarm_data_collection_ui/main.py`)**:
  - `State` dataclass에 `trigger_pressed_right`, `trigger_pressed_left` 상태 추가.
  - VR trigger/grip 신호 (`trigger_right`, `trigger_left`, `grip_right`, `grip_left`) 수신 및 파싱 로직 추가 (값 > 0.5 판단).
  - `/events` SSE 엔드포인트를 통해 VR 트리거 실시간 누름 상태를 프론트엔드로 브로드캐스팅.
  - `load_yaml` 및 `main()`에 metadata 파일 부재 시 안전한 fallback 기본 task 제공 처리.
- **UI 프론트엔드 (`dora-openarm-data-collection-ui/src/dora_openarm_data_collection_ui/templates/root.html`)**:
  - 상단 수집 상태 뱃지 개선 (`🔴 Recording` / `🟢 Idle`).
  - L / R 핸드의 VR 트리거 상태 뱃지 (`PULL (MOVE)` / `OFF`) 실시간 시각화.
  - 레코딩 시작 버튼을 `🔴 Start Recording`으로 명확히 표현 및 수집 종료/저장 버튼 (`✅ Save Episode`, `❌ Discard (Fail)`) 세분화.
- **Dataflow YAML (`dataflow-nana-teleop-sim.yaml`, `dataflow-nana-teleop.yaml`)**:
  - `ui` (`dora-openarm-data-collection-ui`) 및 `recorder` (`dora-openarm-dataset-recorder`) 노드 추가 및 입력/출력 스트림 연결.

## 3. 테스트 및 승인 내용
- `py_compile`을 통한 파이썬 소스 코드 문법 검증 완료.
- 사용자 최종 리뷰 및 검토 승인 완료.
