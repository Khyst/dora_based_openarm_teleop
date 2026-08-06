# openarm_nana_kinematics 리팩토링 및 팔꿈치(Elbow) 트래킹 IK 연동 작업

- **작업 일자**: 2026-08-06
- **작업 분류**: Feature / Refactor / Fix

## 1. 개요 및 목적
1. `nana_v3_dora_teleop_vr` 워크스페이스 내 기존 `openarm_control` 패키지를 `openarm_nana_kinematics`로 변경하여 NaNA v3 기구학에 특화된 패키지 구조로 정리하였습니다.
2. WebXR 데이터 처리 파이프라인에서 전달되는 3D 팔꿈치 포즈(`elbow_right`, `elbow_left`) 데이터를 활용할 수 있도록 `use_elbow` 스위치 플래그 및 팔꿈치 위치(Elbow Position Cost) IK 최적화 제약조건을 추가하였습니다.
3. 로컬 패키지 변경으로 인한 `uv sync` 의존성 해소 이슈를 워크스페이스 설정(`pyproject.toml`) 반영을 통해 해결하였습니다.

## 2. 주요 변경 사항

### 2.1 패키지 리네임 및 구조 변경
- `openarm_control` 디렉토리를 `openarm_nana_kinematics`로 변경.
- 모듈 구조 `src/openarm_control` -> `src/openarm_nana_kinematics`로 변경.
- 내부 소스 코드, 테스트 파일, `pyproject.toml`, `dora-openarm-kinematics`의 import문 및 의존성 명칭 변경.

### 2.2 팔꿈치 트래킹 및 IK 조건부 최적화 (`use_elbow`)
- **`openarm_nana_kinematics/config.py`**:
  - 팔꿈치 프레임 (`nana_v3_right_link4`, `nana_v3_left_link4` 등) 자동 탐색 및 fallback 지원.
  - CLI 옵션 (`--frame-elbow-right`, `--frame-elbow-left` 등) 추가.
- **`openarm_nana_kinematics/ik_params.py`**:
  - `use_elbow: bool = True`, `elbow_cost: float = 0.5` 파라미터 및 CLI 인자 (`--use-elbow`, `--no-use-elbow`, `--elbow-cost`) 추가.
- **`openarm_nana_kinematics/kinematics.py`**:
  - `set_elbow_target(side, position)`, `clear_elbow_target(side)` API 구현.
  - `use_elbow = True`: `mink.FrameTask` / `RelativeFrameTask` 기반 팔꿈치 3D 위치 타겟 비용 함수(Elbow Position Cost)를 QP 최적화 문제에 추가.
  - `use_elbow = False`: 기존 방식대로 6D 손목 타겟만으로 IK 수행.
- **`dora-openarm-kinematics/ik.py`**:
  - dora 입력 채널 (`elbow_right`, `elbow_left`) 이벤트 처리 추가 및 3D 타겟 전달.
- **`dora-openarm-vr/config/dataflow-*-webxr.yaml`**:
  - WebXR 데이터플로우 파일 10종의 `ik` 노드 입력에 `elbow_right: webxr/elbow_right`, `elbow_left: webxr/elbow_left` 연결 추가.

### 2.3 `uv sync` 로컬 워크스페이스 설정
- 워크스페이스 루트 pyproject.toml에 `openarm_nana_kinematics`를 dependencies, `[tool.uv.workspace] members`, `[tool.uv.sources]`에 추가하여 `uv sync` 시 PyPI 대신 로컬 패키지로 의존성 해결 완료.

## 3. 테스트 및 검증
1. `openarm_nana_kinematics` editable 설치 및 파이썬 모듈 테스트 완료.
2. `use_elbow` 파라미터 제어 (`IKParams(use_elbow=True)` / `IKParams(use_elbow=False)`) 동작 확인.
3. `uv sync` 커맨드 정상 실행 (83개 패키지 136ms 해결 완료).
