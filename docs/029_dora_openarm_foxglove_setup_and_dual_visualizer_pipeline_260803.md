# dora-openarm-foxglove 패키지 구현 및 시각화 파이프라인(Foxglove / MuJoCo) 분리 연동

- **작업 일자**: 2026-08-14
- **작업 분류**: Feature / Refactor

## 1. 개요 및 목적
- Web 기반 실시간 원격 시각화 툴인 [Foxglove Studio](https://foxglove.dev/)와의 연동을 위해 `dora-openarm-foxglove` Dora 노드 패키지를 새로 개발하고 워크스페이스에 통합합니다.
- 사용자가 상황에 따라 시각화 엔진(Foxglove WebSocket 또는 MuJoCo GUI 뷰어)을 유연하게 선택하여 실행할 수 있도록 Dataflow YAML 파일 구조를 분리하고 실행 스크립트(`run_sim.sh`, `run_real.sh` 등)에 인자(`foxglove` / `mujoco`) 처리 로직을 적용합니다.

## 2. 주요 변경 사항
- **신규 패키지 구현 (`src/nana_v3_dora_teleop_vr/dora-openarm-foxglove`)**:
  - `pyproject.toml`: `foxglove-websocket`, `dora-rs`, `numpy`, `pyarrow` 의존성 및 CLI 엔트리포인트(`dora-openarm-foxglove`) 등록
  - `schemas.py`: Foxglove 표준 스키마(`foxglove.JointState`, `foxglove.FrameTransforms`, `std_msgs/msg/String`) 및 Custom Quest 텔레메트리 스키마 정의
  - `server.py`:
    - 포트 `8765` 기반 WebSocket 스트리밍 서버 구현
    - `/robot/joint_states`: 14개 관절 및 그리퍼 핑거 상태 실시간 브로드캐스트
    - `/tf`: Quest 3 HMD 및 좌/우 컨트롤러 3D Pose 실시간 변환 발행
    - `/quest/inputs`: 좌/우 트리거(0~100%) 및 버튼(`a`, `b`, `x`, `y`) 상태 스트리밍
    - `/robot_description` 및 3D Mesh 에셋 서빙용 경량 HTTP 서버(포트 `8766`, CORS 지원) 내장
  - `main.py`: Dora 이벤트 비동기 디스패치 루프 및 시그널 처리
  - `tests/test_foxglove_node.py`: 스키마 및 서버 유닛 테스트 5건 작성
- **Dataflow YAML 분리 및 명명 (`dora-openarm-vr/config/`)**:
  - `dataflow-nana-teleop-foxglove.yaml` (실물 + Foxglove)
  - `dataflow-nana-teleop-mujoco.yaml` (실물 + MuJoCo)
  - `dataflow-nana-teleop-sim-foxglove.yaml` (시뮬 + Foxglove)
  - `dataflow-nana-teleop-sim-mujoco.yaml` (시뮬 + MuJoCo)
  - `dataflow-nana-sim.yaml` (중복 심볼릭 링크 정리)
- **실행 스크립트 갱신 (`scripts/`)**:
  - `run_sim.sh`, `run_real.sh`: 시각화 인자(`foxglove` / `mujoco` 또는 `--visualizer`) 지원
  - 콘솔 안내 문구를 `Foxglove Visualizer: ws://localhost:8765`로 통일
- **워크스페이스 설정 갱신 (`pyproject.toml`, `scripts/setup_env.sh`)**:
  - `dora-openarm-foxglove`를 워크스페이스 패키지로 등록 및 `uv sync` 반영

## 3. 테스트 및 승인 내용
- **단위 테스트 검증**: 전체 패키지 유닛 테스트(`pytest`) 8건 100% 통과
- **독립 실행 검증**: WebSocket(`ws://localhost:8765`) 및 Mesh HTTP(`http://localhost:8766`) 정상 서빙 확인
- **스크립트 인자 동작 검증**: `./scripts/run_sim.sh --help`, `./scripts/run_real.sh --help` 및 visualizer 분기 확인 완료
- **사용자 최종 확인**: 변경 사항 검토 후 사용자 커밋 및 원격 푸시 요청 승인 완료
