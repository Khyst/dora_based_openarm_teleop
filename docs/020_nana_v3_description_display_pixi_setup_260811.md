# nana_v3_description display launch 및 pixi 원샷 실행 환경 구축

- **작업 일자**: 2026-08-11
- **작업 분류**: Feature / Fix

## 1. 개요 및 목적
- `nana_v3_description` 패키지의 기존 `display.launch.py`는 존재하지 않는 xacro 파일을 프로세싱하도록 되어 있어, 미리 전처리가 완료된 URDF (`nana_v3_corrected.urdf`)를 직접 읽어 바로 로드할 수 있도록 수정
- RViz2 뷰어 실행 시 인터랙티브 조작 및 마우스 관찰을 위한 Interaction, Move Camera 등의 툴과 디스플레이 설정을 포함하는 RViz 설정 파일 구성
- 외부/시스템 ROS2 환경 독립적으로 isolated 된 환경에서 원클릭으로 RViz2 뷰어를 실행할 수 있도록 `pixi` 환경 구성 및 `run_nana_v3_display.sh` 원샷 스크립트 작성

## 2. 주요 변경 사항
- **`src/nana_v3_description/launch/display.launch.py`**:
  - xacro 프로세싱 제거 후 전처리 완료 URDF(`urdf/nana_v3_corrected.urdf`) 직접 파싱 및 `robot_state_publisher` 전달
  - `model` 및 `rviz_config` LaunchArgument 파라미터화 및 fallback 예외 처리 추가
- **`src/nana_v3_description/rviz/nana_v3_display.rviz`**:
  - `Fixed Frame: world`, `RobotModel`, `Grid`, `TF` 구성
  - `Interact`, `MoveCamera`, `Select`, `FocusCamera`, `Measure` 툴 및 `Toolbar`, `Views` 패널 구성
- **`src/nana_v3_description/CMakeLists.txt`**:
  - `install(DIRECTORY ...)` 설치 대상에 `urdf` 및 `rviz` 디렉터리 추가
- **`pixi.toml`**:
  - `robostack-humble` 및 `conda-forge` 채널 기반 isolated ROS2 환경 의존성 정의
  - `build-v3` 및 `display-v3` pixi task 추가
- **`scripts/run_nana_v3_display.sh`**:
  - `pixi` 환경 동기화, `colcon build`, RViz2 구동 원클릭 쉘 스크립트 작성 및 실행 권한 부여
- **`.gitignore`**:
  - Pixi 가상환경 디렉터리 `.pixi/` 추가

## 3. 테스트 및 승인 내용
- `display.launch.py` 파이썬 구문 검사 및 `run_nana_v3_display.sh` 쉘 구문 검증 완료
- 사용자의 최종 검토 및 승인 확인 후 문서화 및 Git 커밋 진행
