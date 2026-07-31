# 로봇 초기 정합(Initial Alignment) 속도 튜닝 및 진입 개선

- **작업 일자**: 2026-07-31
- **작업 분류**: Performance Optimization / Tuning

## 1. 개요 및 목적
- 초기 VR Grip 시 로봇이 즉시 쫓아오지 않고 한참 지나서야 부드럽게 추종을 시작하던 원인이 초기 정합 단계(`_align`)의 스텝 제한값(`--align-delta-limit 0.0002` = 초당 $0.57^\circ$ 수준의 극저속 개미걸음) 때문임을 규명함.
- 사용자 선택에 따라 안전하면서도 신속하게 $0.6\text{초}$ 이내에 정합 완료(`ALIGNED` 모드 진입)를 보장할 수 있는 `--align-delta-limit 0.003` (초당 약 $8.6^\circ$) 수치로 조율 반영함.

## 2. 주요 변경 사항

- **수정 대상 파일 (총 5개 실물 Dataflow YAML)**:
  1. `config/dataflow-nana-teleop.yaml`
  2. `config/dataflow-nana-teleop-play.yaml`
  3. `config/dataflow-nana-teleop-record.yaml`
  4. `config/dataflow-nana-teleop-data-collection.yaml`
  5. `config/dataflow-data-collection.yaml`

- **변경 내용**:
  - `follower-right` 및 `follower-left` 드라이버 노드의 실행 인자 `--align-delta-limit` 수치를 기존 `0.0002`에서 **`0.003`**으로 변경.

## 3. 테스트 및 승인 내용
- 사용자 질문을 통한 추천 수치(`0.003`) 확정 및 선택 승인.
- 데이터플로우 파이프라인 검증 완료 및 로컬 Git 커밋 완료.
