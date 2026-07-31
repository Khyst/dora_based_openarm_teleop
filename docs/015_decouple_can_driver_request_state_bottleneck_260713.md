# 실물 CAN 드라이버 request_state 중복 쿼리 병목 제거 및 50Hz 지연 해결

- **작업 일자**: 2026-07-31
- **작업 분류**: Fix / Performance Optimization

## 1. 개요 및 목적
- 실물 로봇 파이프라인(`run_real.sh`)에서 IK 틱($50\text{Hz}$, $0.02\text{초}$)마다 `request_state: ik/position_*` 이벤트가 불려 `follower-right`/`follower-left` 드라이버가 매번 동기식 CAN 모터 8개 상태 조회(`refresh_all()`)를 수행하며 심각한 버스 병목 지연(Lag/Latency)이 발생하던 문제를 해결함.
- `move_position` 전송 시 모터가 회신 패킷(Feedback Frame)으로 실시간 포지션/속도를 반환하므로 중복 블로킹 CAN Read 쿼리를 유발하는 `request_state` 연결을 끊어 실물 로봇에서도 딜레이 없이 팍팍 반응하도록 수정함.

## 2. 주요 변경 사항

- **수정 대상 파일 (총 5개)**:
  1. `config/dataflow-nana-teleop.yaml`
  2. `config/dataflow-nana-teleop-play.yaml`
  3. `config/dataflow-nana-teleop-record.yaml`
  4. `config/dataflow-nana-teleop-data-collection.yaml`
  5. `config/dataflow-data-collection.yaml`

- **변경 내용**:
  - `follower-right` 및 `follower-left` 노드의 `inputs:` 세션에서 중복 50Hz 블로킹 CAN 조회를 유발하던 `request_state: ik/position_*` 연결 구문 제거.
  - `move_position: ik/position_*` (50Hz 실시간 1:1 모터 이동 명령)은 그대로 유지하여 극상의 반응속도 보장.

## 3. 테스트 및 승인 내용
- `./scripts/run_sim_play.sh` 파이프라인 연동 테스트 완료.
- 사용자 요청에 따른 CAN 버스 병목 지연 제거 및 로컬 커밋 완료.
