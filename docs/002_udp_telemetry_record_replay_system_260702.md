# VR UDP Telemetry Record & Replay 시스템 및 실행 스크립트 구축

- **작업 일자**: 2026-07-30
- **작업 분류**: Feature / Docs / Refactor

## 1. 개요 및 목적
Meta Quest 3 헤드셋의 VR 조종 데이터(`udp-receiver` 수신 신호 15종)를 ROS 2 Bag처럼 파일로 실시간 녹화(Record)하고, 추후 VR 헤드셋 미연결 상태에서도 동일한 데이터플로우를 재연(Replay) 테스트할 수 있는 `dora-openarm-udp-replay` Dora 노드 패키지 및 전용 실행 스크립트 4종을 개발함. 또한 불필요한 `src/utils/openarm-can-1.2.9` C++ 소스 디렉터리를 정리함.

## 2. 주요 변경 사항
1. **Dora Record & Replay 노드 패키지 개발 (`src/nana_v3_dora_teleop_vr/dora-openarm-udp-replay`)**
   - **`dora-openarm-udp-recorder`**: 수신 15개 신호를 타임스탬프와 함께 JSONL 형식으로 실시간 녹화
   - **`dora-openarm-udp-player`**: 저장된 JSONL 세션 데이터를 기록 시간 간격(`dt`) 및 속도(`--speed`)에 따라 재생 방출 (`--loop` 지원)

2. **Dataflow YAML Config 4종 작성 (`src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/`)**
   - `dataflow-nana-teleop-sim-record.yaml`: 시뮬레이션 조종 & `recordings/vr_sim_session.jsonl` 녹화
   - `dataflow-nana-teleop-sim-play.yaml`: 시뮬레이션 녹화본 재생 (VR 헤드셋 불필요)
   - `dataflow-nana-teleop-record.yaml`: 실물 로봇 조종 & `recordings/vr_real_session.jsonl` 녹화
   - `dataflow-nana-teleop-play.yaml`: 실물 로봇 녹화본 재생 (VR 헤드셋 불필요)

3. **루트 실행 스크립트 4종 추가 및 실행 권한 부여**
   - [`run_sim_record.sh`](file:///home/khy/7.dora_based_openarm_teleop_ws/run_sim_record.sh)
   - [`run_sim_play.sh`](file:///home/khy/7.dora_based_openarm_teleop_ws/run_sim_play.sh)
   - [`run_real_record.sh`](file:///home/khy/7.dora_based_openarm_teleop_ws/run_real_record.sh)
   - [`run_real_play.sh`](file:///home/khy/7.dora_based_openarm_teleop_ws/run_real_play.sh)

4. **문서 및 환경 동기화**
   - [`README.md`](file:///home/khy/7.dora_based_openarm_teleop_ws/README.md)에 Record/Play 모드 및 Hamsa 손 버튼 제어 실행 가이드 작성
   - [`pyproject.toml`](file:///home/khy/7.dora_based_openarm_teleop_ws/pyproject.toml) 업데이트 및 `uv sync` 수행
   - 불필요한 `src/utils/openarm-can-1.2.9` 소스 디렉터리 정리

## 3. 테스트 및 승인 내용
- `dora-openarm-udp-recorder` 및 `dora-openarm-udp-player` CLI 인자 및 PyArrow 방출 단위 테스트 완료
- 스크립트 4종 및 Dataflow Config 정상 작동 검증 및 사용자의 최종 승인 완료
