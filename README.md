# OpenARM Dora Teleoperation Workspace (`dora_based_openarm_teleop`)

본 워크스페이스는 **Dora-rs** 및 **`uv` Workspace** 기반으로 NANA v3 로봇의 VR 원격 제어(Teleoperation) 및 시뮬레이션을 효율적으로 관리하고 실행할 수 있도록 통합 구성된 개발 환경입니다.

---

## 💻 다른 PC에서 Git Clone 후 바로 사용하는 방법

새로운 PC에서 이 저장소를 클론한 후, **단 한 번의 자동화 설치 스크립트 실행**만으로 모든 환경 설정(C++ 의존성 자동 설치, `uv` 설치 및 통합 8개 서브 패키지 동기화)이 완료됩니다.

### 1. 저장소 클론
```bash
git clone https://github.com/Khyst/dora_based_openarm_teleop.git dora_based_openarm_teleop
cd dora_based_openarm_teleop
```

### 2. 자동 환경 설정 실행
```bash
./scripts/setup_env.sh
```

> **자동화 동작 스크립트내용**:
> - `uv` 패키지 관리자 자동 검사 및 설치
> - `openarm-can` C++ 바인딩 컴파일에 필요한 `CLI11` CMake 라이브러리 자동 다운로드 및 설치 (`~/.local`)
> - `src/nana_v3_dora_teleop_vr/` 하위 **전체 8개 서브 패키지** 자동 빌드 및 `.venv` 동기화

---

## 📁 워크스페이스 디렉토리 구조

```
~/dora_based_openarm_teleop/
├── pyproject.toml              # uv workspace 통합 관리 파일 (전체 8개 서브 패키지 통합)
├── README.md                   # 본 사용 가이드 문서
├── scripts/                    # 유틸리티 및 데이터플로우 실행 스크립트 폴더
│   ├── setup_env.sh            # 자동화 환경 설치 및 동기화 스크립트
│   ├── run_sim.sh              # 시뮬레이션(MuJoCo) 실행 스크립트
│   ├── run_sim_record.sh       # 시뮬레이션 실행 + VR 텔레메트리 녹화 스크립트
│   ├── run_sim_play.sh         # 시뮬레이션 상에서 녹화본 재생 스크립트 (VR 헤드셋 미사용)
│   ├── run_real.sh             # 실물 로봇 제어 실행 스크립트
│   ├── run_real_record.sh      # 실물 로봇 제어 + VR 텔레메트리 녹화 스크립트
│   └── run_real_play.sh        # 실물 로봇 상에서 녹화본 재생 스크립트 (VR 헤드셋 미사용)
└── src/
    ├── docs/                   # 프로젝트 파이프라인 & 파라미터 튜닝 문서
    ├── nana_v3_description/    # NANA v3 로봇 모델 (nana_v3.urdf, nana_v3.xml 및 3D Mesh)
    ├── utils/
    │   └── hamsa/              # Hamsa 로봇 손 컨트롤러 라이브러리
    └── nana_v3_dora_teleop_vr/ # Dora 기반 노드 패키지들
        ├── dora-openarm/                  # 실물 팔 Follower 드라이버 노드
        ├── openarm_driver/                # 실물 하드웨어 CAN 통신 드라이버
        ├── dora-openarm-vr/               # VR (Meta Quest) 수신기 & Dataflow YAMLs
        ├── dora-openarm-hamsa/            # VR 버튼 기반 Hamsa 손 동작 토글 노드
        ├── dora-openarm-udp-replay/       # VR UDP 텔레메트리 녹화(Recorder) & 재생(Player) 노드
        ├── dora-openarm-kinematics/       # FK / IK 노드 (openarm-control 기반)
        ├── dora-openarm-mujoco/           # MuJoCo 시뮬레이터 뷰어 노드
        ├── dora-openarm-quitter/          # 안전 종료 및 틱 리더 노드
        ├── dora-openarm-data-collection-ui/ # 데이터 수집 및 상태 컨트롤 UI 노드
        └── dora-openarm-dataset-recorder/   # 데이터셋 기록 노드
```

---

## 🚀 실행 가이드

### 1. 기본 원격 제어 (Live Mode)

#### 1) 시뮬레이션 실행 (Simulation Mode)
VR(Meta Quest 3)로 수신받은 위치 데이터를 **MuJoCo 시뮬레이터** 상의 NANA v3 로봇 모델에 실시간 IK 및 Hamsa 손 제어를 적용하여 확인합니다.
```bash
./scripts/run_sim.sh
```

#### 2) 실물 로봇 원격 제어 실행 (Real Hardware Mode)

> ⚠️ **실물 로봇 제어 전 필수 사전 작업 (CAN FD 설정)**  
> 실물 로봇 제어를 수행하기 전, OpenArm Power Unit의 USB-to-CAN 디바이스 및 SocketCAN 인터페이스(`can0`: 오른팔, `can1`: 왼팔)가 정상 설정되어야 합니다.

##### 🔧 Quick SocketCAN 셋업 (Native Ubuntu)
1. **커널 모듈 로드**:
   ```bash
   sudo modprobe can && sudo modprobe can_raw && sudo modprobe peak_usb
   ```
2. **CAN FD 인터페이스 활성화 (1Mbps Bitrate / 5Mbps Data Bitrate)**:
   ```bash
   # 오른팔 (can0)
   sudo ip link set can0 down 2>/dev/null
   sudo ip link set can0 type can bitrate 1000000 dbitrate 5000000 fd on
   sudo ip link set can0 up

   # 왼팔 (can1)
   sudo ip link set can1 down 2>/dev/null
   sudo ip link set can1 type can bitrate 1000000 dbitrate 5000000 fd on
   sudo ip link set can1 up
   ```
   *(또는 OpenArm 전용 유틸리티 사용: `openarm-can-configure-socketcan can0 -fd -b 1000000 -d 5000000`)*

3. **통신 확인 (오른팔 LED 테스트 등)**:
   ```bash
   candump can0
   # 또는 Joint 1 LED On 명령 전송 테스트: cansend can0 001#FFFFFFFFFFFFFFFC
   ```

> 📖 **상세 셋업 & WSL2 트러블슈팅 가이드**:  
> 패키지 자동 설치, WSL2 커스텀 커널 빌드 및 트러블슈팅 상세 내역은 [`docs/OPENARM_CAN_SETUP_GUIDE.md`](docs/OPENARM_CAN_SETUP_GUIDE.md)를 참고하세요.

##### 실물 제어 스크립트 실행
```bash
./scripts/run_real.sh
```

---

### 2. VR 텔레메트리 녹화 & 재생 가이드 (Record & Playback Mode)

Meta Quest 3 헤드셋이 연결된 상태에서 수신되는 조종 데이터를 녹화(Record)하고, 추후 VR 기기 연결 없이도 ROS 2 Bag 처럼 재생(Replay)하여 동일한 동작을 테스트할 수 있습니다.

#### 1) 녹화 (Record Mode)
- **시뮬레이션 조종 & 녹화**:
  ```bash
  ./scripts/run_sim_record.sh
  ```
  *(수신 데이터는 `recordings/vr_sim_session.jsonl` 파일로 저장됩니다.)*

- **실물 로봇 조종 & 녹화**:
  ```bash
  ./scripts/run_real_record.sh
  ```
  *(수신 데이터는 `recordings/vr_real_session.jsonl` 파일로 저장됩니다.)*

#### 2) 재생 (Playback / Test Mode - VR 헤드셋 불필요)
Meta Quest 3 헤드셋 연결 없이 녹화된 세션 데이터를 재생하여 시뮬레이터 또는 실물 로봇의 동작 및 IK를 재연 테스트합니다.
- **시뮬레이션 상에서 녹화본 재생**:
  ```bash
  ./scripts/run_sim_play.sh
  ```
- **실물 로봇 상에서 녹화본 재생**:
  ```bash
  ./scripts/run_real_play.sh
  ```

---

### 3. 하드웨어 진단 및 제어 (`openarm-can-cli`)

실제 하드웨어 연결 시 `openarm-can-cli` 도구를 사용하여 CAN 통신 상태와 모터 하드웨어를 직접 점검하고 제어할 수 있습니다.

#### 1) CAN 통신 및 모터 상태 모니터링
실제 모터의 실시간 상태(위치, 속도, 토크, 온도 등)를 모니터링하여 CAN 통신이 정상적으로 동작하는지 체크합니다.

```bash
# can0 (오른팔) 모터 상태 실시간 모니터링 (기본 1~8번 모터)
openarm-can-cli -i can0 monitor

# can1 (왼팔) 모터 상태 실시간 모니터링
openarm-can-cli -i can1 monitor

# 특정 모터(예: 1, 2, 3번)만 모니터링할 경우
openarm-can-cli -i can0 monitor --id 1,2,3
```

#### 2) 기타 유용한 진단 및 제어 명령어

- **연결된 모터 검색 (Discover)**: 버스에 연결된 모든 모터의 ID 및 통신 속도를 스캔하여 통신 가능한 모터를 확인합니다.
  ```bash
  openarm-can-cli -i can0 discover
  ```

- **모터 토크 활성화 (Enable)**: 모터의 출력을 켭니다 (Torque ON).
  ```bash
  openarm-can-cli -i can0 enable
  ```

- **모터 토크 비활성화 (Disable)**: 모터의 출력을 끕니다 (Torque OFF).
  ```bash
  openarm-can-cli -i can0 disable
  ```

- **모터 에러 초기화 (Clear Error)**: 모터에 발생한 에러 플래그를 클리어하여 정상 상태로 복구합니다.
  ```bash
  openarm-can-cli -i can0 clear_error
  ```

- **모터 파라미터 확인 (Show Parameter)**: 모터 내부에 설정된 PID 값 및 제한 사항(Limit) 파라미터를 읽어옵니다.
  ```bash
  openarm-can-cli -i can0 show_param
  ```

---

## ✋ Hamsa 로봇 손 VR 버튼 제어 (Hamsa Motion)

VR 컨트롤러의 버튼 입력으로 Hamsa 로봇 손의 동작을 토글 방식으로 조작합니다:
- **Button A**: 오른쪽 손 (Right Grip $\leftrightarrow$ Right Release)
- **Button X**: 왼쪽 손 (Left Grip $\leftrightarrow$ Left Release)
- **Button B**: 오른쪽 손 (Right Scissor $\leftrightarrow$ Right Release)
- **Button Y**: 왼쪽 손 (Left Scissor $\leftrightarrow$ Left Release)

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

- `src/nana_v3_dora_teleop_vr/` 하위의 **모든 서브 패키지**들은 **Editable 모드 (`-e`)** 로 `.venv`에 직접 링크되어 있습니다.
- `src/` 디렉토리 내의 파이썬 소스 코드를 수정하면 별도의 재설치 과정 없이 **즉시 변경 사항이 반영**됩니다.
