# NANA v3 Dora VR Teleoperation Workspace (`13.dora_based_nana_teleop_ws`)

본 워크스페이스는 **Dora-rs** 및 **`uv` Workspace** 기반으로 NANA v3 로봇의 VR 원격 제어(Teleoperation) 및 시뮬레이션을 효율적으로 관리하고 실행할 수 있도록 통합 구성된 개발 환경입니다.

---

## 📁 워크스페이스 디렉토리 구조

```
~/13.dora_based_nana_teleop_ws/
├── pyproject.toml              # uv workspace 통합 관리 파일
├── README.md                   # 본 사용 가이드 문서
├── MANAGEMENT_GUIDE.md        # 상세 환경 관리 및 전략 문서
├── run_sim.sh                  # 시뮬레이션(MuJoCo) 실행 스크립트
├── run_real.sh                 # 실물 로봇 제어 실행 스크립트
└── src/
    ├── nana_v3_description/    # NANA v3 로봇 모델 (nana_v3.urdf, nana_v3.xml 및 3D Mesh)
    └── nana_v3_dora_teleop_vr/ # Dora 기반 노드 패키지들
        ├── dora-openarm-vr/               # VR (Meta Quest) 수신기 & Dataflow YAMLs
        ├── dora-openarm-kinematics/       # FK / IK 노드 (openarm-control 기반)
        ├── dora-openarm-mujoco/           # MuJoCo 시뮬레이터 뷰어 노드
        ├── dora-openarm-quitter/          # 안전 종료 및 틱 리더 노드
        ├── dora-openarm-data-collection-ui/ # 데이터 수집 및 상태 컨트롤 UI 노드
        ├── dora-openarm-dataset-recorder/   # 데이터셋 기록 노드
        ├── dora-openarm/                  # 실물 팔 Follower 드라이버 노드 (하드웨어 전용)
        └── openarm_driver/                # 실물 하드웨어 CAN 통신 드라이버 (하드웨어 전용)
```

---

## 🚀 빠른 시작 (Quick Start)

### 1. 환경 동기화 (`uv sync`)
단 한 번의 명령으로 모든 Dora 노드 패키지와 의존성(Dora-rs, MuJoCo 등)을 동기화합니다:

```bash
cd ~/13.dora_based_nana_teleop_ws
export PATH="$HOME/.local/bin:$PATH"
uv sync
```

---

### 2. 시뮬레이션 실행 (Simulation Mode)

VR(Meta Quest)로 수신받은 위치 데이터를 **MuJoCo 시뮬레이터** 상의 NANA v3 로봇 모델에 실시간 IK 적용하여 확인합니다.

#### 방법 A: 편리한 스크립트 실행
```bash
./run_sim.sh
```

#### 방법 B: `uv` 명령 직접 실행
```bash
uv run dora start src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop-sim.yaml
```

> **Dataflow 구성 노드**: `ui`, `quittable-tick-leader`, `udp-receiver`, `ik`, `mujoco-viewer`

---

### 3. 실물 로봇 원격 제어 실행 (Real Hardware Mode)

실물 NANA v3 로봇과 연결하여 VR 제어를 수행합니다. *(실물 CAN 통신용 `libcli11-dev` 설치 필요)*

```bash
# 하드웨어 드라이버 빌드 환경 동기화
uv sync --extra hardware

# 실물 제어 Dataflow 실행
./run_real.sh
```

---

## 🛠️ Dora 데이터플로우 모니터링 & 조작

Dora 가 실행 중일 때 다음 명령어로 상태 모니터링 및 제어가 가능합니다:

- **실행 중인 데이터플로우 목록 조회**:
  ```bash
  uv run dora list
  ```

- **로그 확인**:
  ```bash
  uv run dora logs <dataflow_uuid> <node_id>
  ```

- **데이터플로우 정지**:
  ```bash
  uv run dora stop <dataflow_uuid>
  ```

---

## 💡 개발 및 코드 수정 안내

- 모든 서브 노드 패키지(`dora-openarm-kinematics`, `dora-openarm-mujoco` 등)는 **Editable 모드 (`-e`)** 로 `.venv`에 링크되어 있습니다.
- `src/` 디렉토리 내의 파이썬 코드를 수정하면 별도의 재설치 과정 없이 **즉시 변경 사항이 반영**됩니다.
