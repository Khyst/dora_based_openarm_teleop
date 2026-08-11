# Pixi 기반 Isolated ROS2 Launch 실행 환경 구축 가이드라인

- **작업 일자**: 2026-08-11
- **작업 분류**: Docs / Guide

---

## 1. 개요 및 목적

본 가이드는 호스트 OS의 전역 ROS2 설치 여부와 상관없이 **Pixi(Conda/Robostack)**를 활용하여 완벽히 격리(Isolated)된 ROS2 환경을 구축하고, `ros2 launch` 및 `colcon build` 명령을 원스톱 스크립트로 실행하는 셋업 가이드라인을 제공합니다.

### Pixi 셋업의 주요 장점
- **환경 독립성**: 시스템 ROS2 환경이나 Python 버전과의 충돌이 전혀 없습니다.
- **재현성 (Reproducibility)**: `pixi.toml` 및 `pixi.lock`을 통해 팀원 전원이 동일한 Conda-forge/Robostack 의존성을 사용합니다.
- **원스톱 실행**: 단 한 줄의 Shell 스크립트 실행으로 환경 동기화, 패키지 빌드, GUI/런칭까지 자동 수행됩니다.

---

## 2. Pixi 설치

시스템에 Pixi 패키지 매니저가 설치되어 있지 않은 경우 아래 명령으로 설치합니다:

```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

설치 완료 후 터미널을 재시작하거나 `export PATH="$HOME/.pixi/bin:$PATH"`를 실행하여 `pixi` 명령어를 활성화합니다.

---

## 3. `pixi.toml` 프로젝트 구성 방법

프로젝트 루트 디렉터리에 `pixi.toml` 파일을 작성하여 Robostack 채널과 ROS2 의존 패키지, 그리고 Pixi task를 정의합니다.

### `pixi.toml` 예시 코드

```toml
[project]
name = "dora_based_openarm_teleop"
version = "0.1.0"
description = "Isolated ROS2 & Teleop Environment"
channels = ["robostack-humble", "conda-forge"]
platforms = ["linux-64"]

[dependencies]
python = ">=3.10"
ros-humble-ros-core = "*"
ros-humble-rviz2 = "*"
ros-humble-robot-state-publisher = "*"
ros-humble-joint-state-publisher-gui = "*"
ros-humble-joint-state-publisher = "*"
ros-humble-xacro = "*"
ros-humble-ament-cmake = "*"
colcon-common-extensions = "*"

[tasks]
build-v3 = "colcon build --packages-select nana_v3_description"
display-v3 = "bash -c 'source install/setup.bash && ros2 launch nana_v3_description display.launch.py'"
```

### 주요 설정 설명
- **`channels`**: ROS2 Humble 패키지를 제공하는 `robostack-humble`과 일반 Conda 패키지를 제공하는 `conda-forge`를 지정합니다.
- **`dependencies`**: 런칭 및 GUI 구동에 필요한 ROS2 패키지들(`ros-humble-rviz2`, `ros-humble-robot-state-publisher` 등)과 빌드 도구(`colcon-common-extensions`)를 지정합니다.
- **`tasks`**:
  - `build-v3`: `colcon build` 명령을 이용해 원하는 ROS2 패키지만 선택 빌드합니다.
  - `display-v3`: 빌드 결과물(`install/setup.bash`)을 sourcing한 뒤 `ros2 launch` 명령어로 실행합니다.

---

## 4. 원클릭 쉘 스크립트 (`.sh`) 구축

사용자가 터미널 명령 한 번으로 의존성 설치, 빌드, 런칭을 모두 수행할 수 있도록 실행 스크립트를 만듭니다.

### `scripts/run_nana_v3_display.sh` 작성 예시

```bash
#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

echo "========================================================"
echo " Launching nana_v3_description RViz2 (Pixi Isolated Env)"
echo "========================================================"

# 1. pixi 명령어 존재 여부 점검
if ! command -v pixi >/dev/null 2>&1; then
    echo "[Error] pixi command not found."
    echo "Please install pixi: curl -fsSL https://pixi.sh/install.sh | bash"
    
    # Fallback option (호스트 ROS2가 있는 경우)
    if [ -f "/opt/ros/humble/setup.bash" ]; then
        echo "Falling back to system ROS2 Humble environment..."
        source /opt/ros/humble/setup.bash
        colcon build --packages-select nana_v3_description
        source install/setup.bash
        ros2 launch nana_v3_description display.launch.py "$@"
        exit 0
    else
        exit 1
    fi
fi

# 2. Pixi 의존성 동기화
echo "[1/3] Synchronizing pixi environment..."
pixi install

# 3. colcon 패키지 빌드
echo "[2/3] Building nana_v3_description package with colcon..."
pixi run build-v3

# 4. ROS2 launch 실행
echo "[3/3] Launching RViz2 display..."
pixi run display-v3 "$@"
```

### 실행 권한 부여
```bash
chmod +x scripts/run_nana_v3_display.sh
```

---

## 5. 셋업 및 실행 명령어

스크립트를 실행하면 Pixi가 필요한 모든 ROS2 바이너리를 `.pixi/` 폴더에 격리 설치하고 바로 launch를 수행합니다.

```bash
./scripts/run_nana_v3_display.sh
```

수동으로 명령어를 분리 실행할 수도 있습니다:
```bash
# 의존성 설치 및 동기화
pixi install

# 패키지 빌드
pixi run build-v3

# ROS2 Launch 구동
pixi run display-v3
```

---

## 6. 주의 사항 및 권장 사항

1. **`.gitignore` 설정**:
   - Pixi가 가상환경을 구축하면서 생성하는 `.pixi/` 폴더는 용량이 크므로 버전 관리에서 제외해야 합니다.
   - `.gitignore`에 `.pixi/` 항목을 추가합니다.

2. **URDF / Launch 파라미터화**:
   - `display.launch.py` 내에서 전처리된 `.urdf` 파일 경로를 받아들일 수 있도록 `DeclareLaunchArgument("model", ...)`과 `OpaqueFunction`을 활용하면 런칭 시 유연성이 크게 향상됩니다.
