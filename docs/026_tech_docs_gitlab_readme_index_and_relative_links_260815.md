# GitLab tech_docs README 구성 및 상대 경로 링크 수정 가이드

- **작업 일자**: 2026-08-12
- **작업 분류**: Feature / Docs

## 1. 개요 및 목적
- GitLab 웹 인터페이스에서 `tech_docs` 폴더로 이동했을 때 인덱스 문서(`99_dora_openarm_teleop_index.md`)가 기본 화면(`README.md`)으로 자동 렌더링되도록 개선.
- 인덱스 문서 내 아키텍처 컴포넌트 링크를 절대 경로(`file:///...`)에서 상대 경로(`./...`)로 변경하여 GitLab 상에서 클릭 시 해당 기술 문서로 바로 이동할 수 있도록 수정.

## 2. 주요 변경 사항
- **`tech_docs/README.md` 생성**: `99_dora_openarm_teleop_index.md` 내용 기반으로 `README.md`를 생성하여 GitLab 폴더 진입 시 자동으로 메인 뷰어로 표시되도록 설정.
- **상대 경로 링크 수정**:
  - `00_nana_openarm_description.md` ~ `05_dora_openarm.md` 문서 링크를 `./00_nana_openarm_description.md` 형태로 변경.
- **아키텍처 다이어그램 이미지 호환**:
  - `tech_docs/dora_based_openarm_teleop_diagram.jpg` 복사 배치 및 `![dora_based_openarm_teleop_diagram](./dora_based_openarm_teleop_diagram.jpg)` 구문 적용.
- **로컬 저장소 동기화**: `sync_to_local.sh` 실행을 통해 `dora_based_openarm_teleop_local` 폴더에도 동일하게 반영.

## 3. 테스트 및 승인 내용
- GitLab 웹 UI 호환성 검증 및 `tech_docs` 렌더링/바로가기 링크 기능 사용자 승인 완료.
