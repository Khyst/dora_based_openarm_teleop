# 초기 정합(Initial Alignment) 설정 원본 오픈소스 수치(0.0002) 원복

- **작업 일자**: 2026-07-31
- **작업 분류**: Revert / Configuration

## 1. 개요 및 목적
- 사용자 지시에 따라 정합 준비 자세(Ready Pose / 팔꿈치 구부림 자세) 변경을 통한 테스트를 진행하기 위해, `--align-delta-limit` 설정 인자를 원본 오픈소스 상태 기본값인 **`0.0002`**로 원복함.

## 2. 주요 변경 사항

- **복구 대상 파일 (총 5개 실물 Dataflow YAML)**:
  1. `config/dataflow-nana-teleop.yaml`
  2. `config/dataflow-nana-teleop-play.yaml`
  3. `config/dataflow-nana-teleop-record.yaml`
  4. `config/dataflow-nana-teleop-data-collection.yaml`
  5. `config/dataflow-data-collection.yaml`

- **변경 내용**:
  - `follower-right` 및 `follower-left` 드라이버 노드의 실행 인자 `--align-delta-limit` 수치를 원본 상태인 **`0.0002`**로 원복.

## 3. 테스트 및 승인 내용
- 사용자 요청에 따른 원본 오픈소스 인자 수치 원복 및 로컬 Git 커밋 완료.
