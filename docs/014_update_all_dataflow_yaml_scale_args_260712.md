# 전체 Dataflow YAML의 VR 스케일 파라미터 업데이트 (scale_y 1.0 표준 적용)

- **작업 일자**: 2026-07-31
- **작업 분류**: Config / Scaling Update

## 1. 개요 및 목적
- `dora-openarm-vr/config/` 폴더 내의 전체 9개 Dataflow YAML 설정 파일의 `udp-receiver` 노드 인자(`args`)를 기본 표준값인 **`scale_y 1.0`** (1:1 선형 매핑)으로 업데이트함.
- `quest_receiver.py` 내의 `scale_y` 파라미터 default 값도 동일하게 `1.0`으로 기본 동기화함.

## 2. 주요 변경 사항

- **대상 파일**: `src/nana_v3_dora_teleop_vr/dora-openarm-vr/src/dora_openarm_vr/quest_receiver.py` 및 `config/*.yaml` 9종
- **수정 내용**:
  1. `quest_receiver.py` default `scale_y = 1.0`으로 설정.
  2. Dataflow YAML 9종의 `udp-receiver` 인자를 아래와 같이 일괄 적용:
  ```yaml
  args: "--host 0.0.0.0 --port 5006 --scale-x 1.0 --scale-y 1.0 --scale-z 1.0"
  ```

## 3. 테스트 및 승인 내용
- `./scripts/run_sim_play.sh` 파이프라인 연동 및 정상 실행 검증 완료.
- 사용자 요청에 따른 `scale_y 1.0` 일괄 반영 완료.
