# dora-openarm-dataset-recorder 패키지 셋업 및 워크스페이스 연동

- **작업 일자**: 2026-08-14
- **작업 분류**: Feature

## 1. 개요 및 목적
- 향후 텔레오퍼레이션 데이터셋 수집 및 기록 작업을 수행할 수 있도록, OpenArm 데이터셋 레코더 노드 저장소(`https://github.com/enactic/dora-openarm-dataset-recorder`)를 워크스페이스 내 `nana_v3_dora_teleop_vr` 하위 패키지로 셋업하고 `uv` 워크스페이스 환경에 연동합니다.

## 2. 주요 변경 사항
- **패키지 클론 및 모노레포화**:
  - `src/nana_v3_dora_teleop_vr/dora-openarm-dataset-recorder` 경로로 소스코드 셋업
  - 하위 `.git` 메타데이터 디렉토리를 제거하여 루트 메인 모노레포에 포함
- **uv 워크스페이스 설정 갱신 (`pyproject.toml`)**:
  - `project.dependencies`에 `dora-openarm-dataset-recorder` 추가
  - `tool.uv.workspace.members`에 `src/nana_v3_dora_teleop_vr/dora-openarm-dataset-recorder` 등록
  - `tool.uv.sources`에 `dora-openarm-dataset-recorder = { workspace = true }` 등록
- **환경 설정 스크립트 수정 (`scripts/setup_env.sh`)**:
  - 동기화 대상 워크스페이스 패키지 개수 주석 갱신 (8개 -> 9개)
- **가상환경 동기화 (`uv.lock`)**:
  - `uv sync`를 통해 가상환경에 `dora-openarm-dataset-recorder` (v0.4.0) 빌드 및 패키지 설치 완료

## 3. 테스트 및 승인 내용
- **모듈 임포트 검증**: `uv run python3 -c "import dora_openarm_dataset_recorder"` 정상 실행
- **CLI 진입점 검증**: `uv run dora-openarm-dataset-recorder --help` 실행 및 옵션 확인 완료
- **단위 테스트 통과**: `uv run --with pytest pytest src/nana_v3_dora_teleop_vr/dora-openarm-dataset-recorder/tests` 3개 테스트 케이스 100% 통과
- **사용자 승인 완료**: 변경 사항 공유 후 사용자 최종 커밋 진행 승인 완료
