# dora_openarm_kinematics_control 패키지 모듈화 및 이관

- **작업 일자**: 2026-08-12
- **작업 분류**: Feature / Refactor

## 1. 개요 및 목적
- 기존 `.venv` 환경에 가상환경 라이브러리로 설치되어 있던 사용자 커스텀 `openarm_control` 패키지 소스 코드가 pip 업데이트 또는 환경 재구축 시 유실되는 문제를 방지하기 위함.
- 프로젝트 내 `src/nana_v3_dora_teleop_vr/dora-openarm-kinematics-control`로 소스 코드를 이관 및 정립하고, `dora_teleop_vr` 파이프라인이 로컬 내장 패키지를 참조하도록 개편함.

## 2. 주요 변경 사항
1. **내장 패키지 생성 (`dora-openarm-kinematics-control`)**:
   - 위치: `src/nana_v3_dora_teleop_vr/dora-openarm-kinematics-control`
   - Python 패키지 배포명: `dora-openarm-kinematics-control`
   - Python 모듈/임포트명: `dora_openarm_kinematics_control`
   - `config.py`, `kinematics.py`, `poses.py` 내부 임포트를 상대 임포트로 수정
   - `pyproject.toml` 및 `README.md` 작성

2. **워크스페이스 의존성 갱신**:
   - 루트 `pyproject.toml`의 `members`, `sources`, `dependencies`에 `dora-openarm-kinematics-control` 추가
   - `src/nana_v3_dora_teleop_vr/dora-openarm-kinematics/pyproject.toml` 의존성을 `openarm-control`에서 `dora-openarm-kinematics-control`로 수정

3. **`dora_openarm_kinematics` 노드 임포트 수정**:
   - `fk.py`, `ik.py`에서 `openarm_control` 대신 `dora_openarm_kinematics_control`을 임포트하도록 전환

4. **환경 동기화 (`uv sync`)**:
   - `.venv` 내 외부 PyPI `openarm-control` 패키지 자동 제거 및 로컬 `dora-openarm-kinematics-control` editable 등록 완료

## 3. 테스트 및 승인 내용
- 사용자 검토 요청 및 결과 승인 완료 (`커밋 해줘` 요청 확인).
- Python 모듈 임포트 테스트 (`import dora_openarm_kinematics_control`, `import dora_openarm_kinematics.ik`) 성공적 검증.
