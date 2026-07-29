# NANA v3 Dora Teleop Workspace 환경 관리 및 운용 전략 (`MANAGEMENT_GUIDE.md`)

## 1. 관리 전략 배경 및 목표

기존 Dora 데이터플로우 실행 구조에서는 각 노드(`dora-openarm-kinematics`, `dora-openarm-mujoco` 등)마다 개별적인 파이썬 환경 구축이나 노드별 `pip install -e` 빌드 과정이 필요하여, 환경 간 패키지 버전 충돌 및 빌드 파편화 문제가 존재했습니다.

이를 해결하기 위해 본 워크스페이스는 **`uv` Workspace 기법**을 도입하여 다음과 같은 관리 전략을 적용했습니다:

1. **단일 가상환경 통합 (Unified Virtual Environment)**: Root `pyproject.toml`에 Workspace Member를 등록하여 전체 프로젝트 노드들을 하나의 `.venv`에서 통합 관리.
2. **Editable 모드 즉시 동기화**: 모든 서브 노드를 `-e` (Editable) 링크하여 코드 수정 시 별도 빌드/재설치 없이 즉각 반영.
3. **시뮬레이션 / 하드웨어 의존성 분리**: C++ 컴파일이 필요한 실물 로봇 드라이버(`openarm_driver`, `dora-openarm`)를 `optional-dependencies` (`extra = hardware`)로 분리하여 C++ 환경 라이브러리가 없는 환경에서도 시뮬레이션 데이터플로우가 100% 독립 동작하도록 보장.

---

## 2. Workspace `pyproject.toml` 구조 분석

```toml
[project]
name = "dora-based-nana-teleop-ws"
version = "0.1.0"
description = "Workspace for Dora-based NANA v3 VR Teleoperation"
requires-python = ">=3.11"
dependencies = [
    "dora-rs>=0.5.0",
    "dora-rs-cli>=0.5.0",
    "dora-openarm-vr",
    "dora-openarm-kinematics",
    "dora-openarm-mujoco",
    "dora-openarm-quitter",
    "dora-openarm-data-collection-ui",
    "dora-openarm-dataset-recorder",
]

[project.optional-dependencies]
hardware = [
    "dora-openarm",
    "openarm-driver",
]

[tool.uv.workspace]
members = [
    "src/nana_v3_dora_teleop_vr/dora-openarm-vr",
    "src/nana_v3_dora_teleop_vr/dora-openarm-data-collection-ui",
    "src/nana_v3_dora_teleop_vr/dora-openarm-dataset-recorder",
    "src/nana_v3_dora_teleop_vr/dora-openarm-kinematics",
    "src/nana_v3_dora_teleop_vr/dora-openarm-mujoco",
    "src/nana_v3_dora_teleop_vr/dora-openarm-quitter",
]

[tool.uv.sources]
dora-openarm-vr = { workspace = true }
dora-openarm-kinematics = { workspace = true }
dora-openarm-mujoco = { workspace = true }
dora-openarm-quitter = { workspace = true }
dora-openarm-data-collection-ui = { workspace = true }
dora-openarm-dataset-recorder = { workspace = true }
dora-openarm = { path = "src/nana_v3_dora_teleop_vr/dora-openarm", editable = true }
openarm-driver = { path = "src/nana_v3_dora_teleop_vr/openarm_driver", editable = true }
```

---

## 3. Dataflow 비교 및 실행 원리

### 3.1 `dataflow-nana-teleop-sim.yaml` (시뮬레이션 전용)
- **목적**: VR Quest 조작 데이터를 수신하여 Kinematics(IK)를 계산하고, 결과를 MuJoCo 3D 시뮬레이터 뷰어에 실시간 렌더링.
- **실행 명령**:
  ```bash
  uv run dora start src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop-sim.yaml
  ```
- **포함 노드**:
  - `ui`: 버튼 제어 및 데이터 수집 상태 제어
  - `quittable-tick-leader`: 시스템 틱 및 안전 정지 타이머
  - `udp-receiver`: Quest VR 컨트롤러 포즈 UDP 수신
  - `ik`: NANA v3 URDF/XML 모델 기준 역운동학 계산
  - `mujoco-viewer`: MuJoCo 시각화

### 3.2 `dataflow-nana-teleop.yaml` (실물 로봇 제어)
- **목적**: 시뮬레이션 기능에 더해 양팔 실물 로봇(`follower-left`, `follower-right`) 하드웨어 드라이버를 직접 구동.
- **필요 사전 작업**: `libcli11-dev` C++ 헤더 패키지 설치 후 `uv sync --extra hardware` 수행
- **실행 명령**:
  ```bash
  uv run dora start src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop.yaml
  ```

---

## 4. 트러블슈팅 및 유용한 명령어

1. **새로운 의존성 추가 시**:
   ```bash
   uv add <package_name>
   ```

2. **환경 리셋 후 재구축**:
   ```bash
   rm -rf .venv
   uv sync
   ```

3. **Dora Daemon 문제 발생 시 리셋**:
   ```bash
   uv run dora destroy
   ```
