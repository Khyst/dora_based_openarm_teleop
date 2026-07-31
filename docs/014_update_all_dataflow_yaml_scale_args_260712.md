# 전체 Dataflow YAML의 VR 스케일 파라미터 업데이트 (scale_y 1.25 적용)

- **작업 일자**: 2026-07-31
- **작업 분류**: Config / Scaling Update

## 1. 개요 및 목적
- 보정된 NANA v3 로봇의 넓어진 어깨 폭($36\text{cm}$)에 맞추어, `dora-openarm-vr/config/` 폴더 내의 전체 9개 Dataflow YAML 설정 파일의 `udp-receiver` 노드 인자(`args`)를 일괄 업데이트함.
- Y축 스케일 가중치를 **`1.25`**로 지정하여 VR 컨트롤러 손 동작 시 로봇 팔이 시원시원하게 바깥으로 벌어지도록 체감 감도를 보정함.

## 2. 주요 변경 사항

- **대상 디렉토리**: `src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/`
- **수정 파일 목록 (총 9개)**:
  1. `dataflow-data-collection.yaml`
  2. `dataflow-mujoco-data-collection.yaml`
  3. `dataflow-mujoco.yaml`
  4. `dataflow-nana-teleop-data-collection.yaml`
  5. `dataflow-nana-teleop-record.yaml`
  6. `dataflow-nana-teleop-sim-data-collection.yaml`
  7. `dataflow-nana-teleop-sim-record.yaml`
  8. `dataflow-nana-teleop-sim.yaml`
  9. `dataflow-nana-teleop.yaml`

- **변경 인자 내용**:
  ```yaml
  # 변경 전:
  args: "--host 0.0.0.0 --port 5006"

  # 변경 후:
  args: "--host 0.0.0.0 --port 5006 --scale-x 1.0 --scale-y 1.25 --scale-z 1.0"
  ```

## 3. 테스트 및 승인 내용
- `./scripts/run_sim_play.sh` 파이프라인 연동 및 정상 실행 검증 완료.
- 사용자 요청에 따른 일괄 반영 및 로컬 커밋 완료.
