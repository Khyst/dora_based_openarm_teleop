# NANA v3 Dora VR Teleoperation Workspace (`13.dora_based_nana_teleop_ws`)

본 워크스페이스는 **Dora-rs** 및 **`uv` Workspace** 기반으로 NANA v3 로봇의 VR 원격 제어(Teleoperation) 및 시뮬레이션을 효율적으로 관리하고 실행할 수 있도록 통합 구성된 개발 환경입니다.

---

## 💻 다른 PC에서 Git Clone 후 바로 사용하는 방법

새로운 PC에서 이 저장소를 클론한 후, **단 한 번의 자동화 설치 스크립트 실행**만으로 모든 환경 설정(C++ 의존성 자동 설치, `uv` 설치 및 통합 8개 서브 패키지 동기화)이 완료됩니다.

### 1. 저장소 클론
```bash
git clone <YOUR_REMOTE_REPO_URL> 13.dora_based_nana_teleop_ws
cd 13.dora_based_nana_teleop_ws
```

### 2. 자동 환경 설정 실행
```bash
./setup_env.sh
```

> **자동화 동작 스크립트내용**:
> - `uv` 패키지 관리자 자동 검사 및 설치
> - `openarm-can` C++ 바인딩 컴파일에 필요한 `CLI11` CMake 라이브러리 자동 다운로드 및 설치 (`~/.local`)
> - `src/nana_v3_dora_teleop_vr/` 하위 **전체 8개 서브 패키지** 자동 빌드 및 `.venv` 동기화

---

## 📁 워크스페이스 디렉토리 구조

```
~/13.dora_based_nana_teleop_ws/
├── setup_env.sh                # 자동화 환경 설치 및 동기화 스크립트
├── pyproject.toml              # uv workspace 통합 관리 파일 (전체 8개 서브 패키지 통합)
├── README.md                   # 본 사용 가이드 문서
├── MANAGEMENT_GUIDE.md        # 상세 환경 관리 및 전략 문서
├── run_sim.sh                  # 시뮬레이션(MuJoCo) 실행 스크립트
├── run_real.sh                 # 실물 로봇 제어 실행 스크립트
└── src/
    ├── nana_v3_description/    # NANA v3 로봇 모델 (nana_v3.urdf, nana_v3.xml 및 3D Mesh)
    └── nana_v3_dora_teleop_vr/ # Dora 기반 노드 패키지들 (8개 통합 패키지)
        ├── dora-openarm/                  # 실물 팔 Follower 드라이버 노드
        ├── openarm_driver/                # 실물 하드웨어 CAN 통신 드라이버
        ├── dora-openarm-vr/               # VR (Meta Quest) 수신기 & Dataflow YAMLs
        ├── dora-openarm-kinematics/       # FK / IK 노드 (openarm-control 기반)
        ├── dora-openarm-mujoco/           # MuJoCo 시뮬레이터 뷰어 노드
        ├── dora-openarm-quitter/          # 안전 종료 및 틱 리더 노드
        ├── dora-openarm-data-collection-ui/ # 데이터 수집 및 상태 컨트롤 UI 노드
        └── dora-openarm-dataset-recorder/   # 데이터셋 기록 노드
```

---

## 🚀 실행 가이드

### 1. 시뮬레이션 실행 (Simulation Mode)

VR(Meta Quest)로 수신받은 위치 데이터를 **MuJoCo 시뮬레이터** 상의 NANA v3 로봇 모델에 실시간 IK 적용하여 확인합니다.

```bash
./run_sim.sh
```

*(또는 `uv run dora run src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop-sim.yaml`)*

> **Dataflow 구성 노드**: `ui`, `quittable-tick-leader`, `udp-receiver`, `ik`, `mujoco-viewer`

---

### 2. 실물 로봇 원격 제어 실행 (Real Hardware Mode)

실물 NANA v3 로봇과 연결하여 VR 원격 제어를 수행합니다. (`nana_v3_dora_teleop_vr` 하위의 `dora-openarm` 및 `openarm_driver` 직접 사용)

```bash
./run_real.sh
```

*(또는 `uv run dora run src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop.yaml`)*

> **Dataflow 구성 노드**: `ui`, `quittable-tick-leader`, `udp-receiver`, `ik`, `mujoco-viewer`, `follower-left`, `follower-right`

---

## 🛠️ Dora 데이터플로우 모니터링 & 조작

Dora 실행 중 다른 터미널에서 다음 명령어로 상태 모니터링 및 제어가 가능합니다:

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

- `src/nana_v3_dora_teleop_vr/` 하위의 **모든 8개 서브 패키지**(`dora-openarm`, `openarm_driver`, `dora-openarm-kinematics` 등)는 **Editable 모드 (`-e`)** 로 `.venv`에 직접 링크되어 있습니다.
- `src/` 디렉토리 내의 파이썬 소스 코드를 수정하면 별도의 재설치 과정 없이 **즉시 변경 사항이 반영**됩니다.
