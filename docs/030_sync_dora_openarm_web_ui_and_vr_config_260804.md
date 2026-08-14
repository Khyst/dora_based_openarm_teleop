# dora-openarm-web-ui 동기화 및 VR Dataflow Config 연동

- **작업 일자**: 2026-08-14
- **작업 분류**: Feature / Refactor

## 1. 개요 및 목적
- `dora_based_openarm_teleop_local`에서 개발된 Three.js & WebGL 기반 3D 웹 뷰어 및 궤적 수집 패키지인 `dora-openarm-web-ui`를 메인 저장소(`dora_based_openarm_teleop`)로 동기화.
- `dora-openarm-vr`의 모든 Dataflow 설정 파일에 `web-ui` 노드를 연동하고, 실행 스크립트(`run_sim.sh`, `run_real.sh`)를 개선.
- 에피소드 데이터셋(JSON) 저장 시 불필요한 `triggers`와 `buttons` 필드를 제외하고, CLI/환경변수 인자를 통해 `waypoints`(기본값) 또는 `trajectories` 중 선택하여 저장하도록 기능 구현.

## 2. 주요 변경 사항
1. **`dora-openarm-web-ui` 패키지 동기화 및 워크스페이스 등록**:
   - `src/nana_v3_dora_teleop_vr/dora-openarm-web-ui/` 소스 코드 및 리소스 동기화.
   - `pyproject.toml`에 워크스페이스 패키지 멤버 및 의존성 등록, `uv sync` 적용.
2. **`dora-openarm-vr` Config 파일 업데이트**:
   - `dataflow-nana-teleop.yaml`, `dataflow-nana-teleop-sim.yaml`, `dataflow-nana-teleop-mujoco.yaml`, `dataflow-nana-teleop-sim-mujoco.yaml`, `dataflow-nana-teleop-foxglove.yaml`, `dataflow-nana-teleop-sim-foxglove.yaml`에 `web-ui` 노드 통합.
   - `test_metadata.yaml` 추가.
3. **데이터셋 저장 정제 및 모드 분기 (Selective Dataset Recording)**:
   - `root.html` 및 `main.py`에서 JSON 저장 시 `triggers`, `buttons` 필드 제외.
   - `--record-type` (`waypoints` 기본값 / `trajectories`) 인자 및 `RECORD_TYPE` 환경변수 지원.
4. **실행 스크립트 개선**:
   - `scripts/run_sim.sh`, `scripts/run_real.sh`에 `web` 뷰어 기본 적용 및 `waypoints`/`trajectories` 인자 지원.

## 3. 테스트 및 승인 내용
- `uv sync`를 통한 패키지 설치 및 의존성 해결 검증 완료.
- `python -m dora_openarm_web_ui.main --help` 및 `./scripts/run_sim.sh --help`, `./scripts/run_real.sh --help` 옵션 파싱 동작 검증.
- 사용자의 최종 검토 및 커밋/푸시 승인 완료.
