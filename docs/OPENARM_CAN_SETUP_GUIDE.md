# OpenArm (AA-K1) CAN & CAN FD 초기 셋업 가이드라인

본 문서는 **Libertron OpenArm (AA-K1)** 로봇 시스템의 CAN / SocketCAN 통신을 기본 설치부터 문제 해결까지 수행할 수 있도록 작성된 가이드라인입니다. **Native Ubuntu** 및 **Windows (WSL2)** 환경 모두에 대해 단계별 셋업 절차를 안내합니다.

---

## 1. 개요 및 하드웨어 사양

* **하드웨어 디바이스**: OpenArm (AA-K1) Power Unit 내장 USB-to-CAN FD 컨버터 (PEAK PCAN-USB Pro FD 디바이스)
* **인터페이스 할당 규칙 (매뉴얼 Section 7.1)**:
  * **낮은 번호 (`can0`)**: 오른쪽 팔 (Right Arm)
  * **높은 번호 (`can1`)**: 왼쪽 팔 (Left Arm)
* **CAN FD 통신 설정 값 (매뉴얼 Section 6.2)**:
  * **Nominal Bitrate**: 1 Mbps (`1000000`)
  * **Data Bitrate**: 5 Mbps (`5000000`)
  * **Mode**: CAN FD 활성화 (`fd on`)

---

## 2. [추천] Native Ubuntu 환경 초기 셋업 (22.04 / 24.04)

OpenArm과 같은 로봇 제어 시스템은 고속 CAN FD 통신의 실시간성(Low-latency)이 필수적이므로 **Native Ubuntu 환경 사용을 가장 권장**합니다.

### 2.1. 필수 소프트웨어 패키지 설치
터미널에서 SocketCAN 유틸리티 및 OpenArm CAN 라이브러리를 설치합니다:

```bash
# 기본 CAN 유틸리티 설치
sudo apt update
sudo apt install -y can-utils iproute2 software-properties-common

# OpenArm 공식 PPA 패키지 설치
sudo add-apt-repository -y ppa:openarm/main
sudo apt update
sudo apt install -y libopenarm-can-dev openarm-can-utils
```

### 2.2. 하드웨어 연결 및 디바이스 인식 확인
Power Unit의 AC 전원과 로봇 연결 케이블, 그리고 **USB-B 케이블**을 PC에 연결한 후 아래 명령으로 확인합니다:

1. **USB 디바이스 인식 확인**:
   ```bash
   lsusb
   ```
   * 목록에 `PEAK System PCAN-USB Pro FD` 또는 관련 CAN 디바이스가 표시되어야 합니다.

2. **네트워크 인터페이스 확인**:
   ```bash
   ip link show
   ```
   * 목록에 `can0`, `can1` 인터페이스가 나타나는지 확인합니다.

3. **필요 시 커널 모듈 수동 로드**:
   인터페이스가 즉시 나타나지 않는 경우 커널 모듈을 로드합니다:
   ```bash
   sudo modprobe can
   sudo modprobe can_raw
   sudo modprobe peak_usb
   ```

### 2.3. CAN FD 인터페이스 설정 및 활성화
`can0` (오른팔) 및 `can1` (왼팔)에 대해 CAN FD 속도를 설정하고 올려줍니다.

**방법 A: OpenArm 전용 구성 명령어 사용 (권장)**
```bash
openarm-can-configure-socketcan can0 -fd -b 1000000 -d 5000000
openarm-can-configure-socketcan can1 -fd -b 1000000 -d 5000000
```

**방법 B: Linux `ip` 명령어 수동 설정**
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

> ⚠️ **주의**: SocketCAN 구성은 비휘발성이 아니므로 PC를 재부팅하거나 USB 케이블을 재연결할 때마다 설정을 다시 실행해야 합니다.

### 2.4. 통신 테스트
1. **CAN 트래픽 모니터링**:
   ```bash
   candump can0
   ```
2. **테스트 명령 전송 (Joint 1 관절 LED On/Off 테스트)**:
   ```bash
   # Joint 1 LED 켜기 (Enable)
   cansend can0 001#FFFFFFFFFFFFFFFC

   # Joint 1 LED 끄기 (Disable)
   cansend can0 001#FFFFFFFFFFFFFFFD
   ```

---

## 3. Windows (WSL2) 환경 초기 셋업 및 트러블슈팅

WSL2 환경에서는 **USB Passthrough 설정**과 **WSL2 Linux 커널의 CAN 드라이버 지원 여부**를 추가로 처리해야 합니다.

### 3.1. Windows에서 WSL2로 USB 패스스루 (`usbipd-win`)
Windows 호스트에 꽂힌 USB-to-CAN 디바이스를 WSL2 내부로 전달합니다.

1. **Windows PowerShell (관리자 권한)에서 `usbipd-win` 설치**:
   ```powershell
   winget install --interactive --exact dorssel.usbipd-win
   ```
   *(설치 후 PowerShell 창을 닫고 관리자 권한으로 다시 열어주세요.)*

2. **USB 디바이스 BUSID 확인**:
   ```powershell
   usbipd list
   ```
   * 목록에서 `PCAN-USB Pro FD` 디바이스의 BUSID(예: `2-3`)를 확인합니다.

3. **바인딩 및 WSL2 연결**:
   ```powershell
   # 바인딩 (필요 시 --force)
   usbipd bind --force --busid 2-3

   # WSL2로 연결 (usbipd 4.x/5.x 기준 --wsl 옵션 필수)
   usbipd attach --wsl --busid 2-3
   ```

### 3.2. WSL2 커스텀 커널 빌드 (`peak_usb` 드라이버 미지원 문제 해결)
Microsoft에서 기본 제공하는 WSL2 커널(`*-microsoft-standard-WSL2`)에는 PEAK USB CAN 드라이버(`peak_usb.ko`)가 빌드되어 있지 않아 `sudo modprobe peak_usb` 시 `FATAL: Module peak_usb not found` 오류가 발생합니다.

WSL2에서 CAN을 동작시키려면 커스텀 커널 빌드가 필요합니다:

1. **WSL2 리눅스 터미널에서 커널 소스 및 빌드 도구 준비**:
   ```bash
   sudo apt update
   sudo apt install -y build-essential flex bison libssl-dev libelf-dev libncurses-dev git
   git clone --depth 1 -b linux-msft-wsl-6.6.y https://github.com/microsoft/WSL2-Linux-Kernel.git
   cd WSL2-Linux-Kernel
   ```

2. **커널 설정 (`make menuconfig`)**:
   ```bash
   zcat /proc/config.gz > .config
   make menuconfig
   ```
   * `Networking support` → `CAN bus subsystem support` (`CONFIG_CAN`) → `<M>` 또는 `<*>` 선택
   * `CAN Device Drivers` → `CAN USB interfaces` (`CONFIG_CAN_PEAK_USB`) → `<M>` 또는 `<*>` 선택

3. **커널 및 모듈 컴파일**:
   ```bash
   make -j$(nproc) KCONFIG_CONFIG=.config
   sudo make modules_install
   ```

4. **Windows `.wslconfig` 설정**:
   * Windows 사용자 홈 디렉토리(`C:\Users\<사용자명>\.wslconfig`) 파일을 생성 또는 편집합니다:
     ```ini
     [wsl2]
     kernel=C:\\path\\to\\WSL2-Linux-Kernel\\vmlinux
     ```

5. **WSL2 재부팅**:
   * Windows PowerShell에서 `wsl --shutdown` 실행 후 WSL2 재접속.

6. **WSL2 접속 후 확인**:
   * `usbipd attach --wsl --busid 2-3` 실행 후 WSL2에서 `lsusb` 및 `ip link show`로 `can0`, `can1` 표시 확인.

---

## 4. 트러블슈팅 (Troubleshooting Checklist)

| 현상 | 원인 | 조치 사항 |
| :--- | :--- | :--- |
| `Cannot find device "can0"` | `ip link show`에 `can0`이 등록되지 않은 상태에서 설정 명령어 실행 | 1. Power Unit 전원 및 E-Stop 버튼 확인<br>2. USB-B 케이블 연결 점검<br>3. `lsusb`로 물리적 인식 여부 확인<br>4. `sudo modprobe peak_usb`로 커널 모듈 로드 |
| `modprobe: FATAL: Module peak_usb not found` | WSL2 기본 커널에 PEAK CAN 드라이버 미포함 | 1. **Native Ubuntu 환경 사용 권장**<br>2. WSL2 사용 시 커스텀 커널 빌드 진행 |
| `usbipd: error: The 'wsl' subcommand has been removed` | `usbipd-win` v4.0 이상 버전 변경사항 | `usbipd attach --wsl --busid <BUSID>` 구문 사용 |
| `candump can0` 실행 시 반응 없음 | CAN FD 속도 미설정 또는 인터페이스 DOWN 상태 | 1. `ip link show can0`으로 `UP` 상태인지 확인<br>2. bitrate 1Mbps, dbitrate 5Mbps 설정 재실행 |
| 액추에이터 일부 미인식 | 케이블 결착 불량 | 액추에이터 커넥터 전원/통신 핀 재결착 (매뉴얼 Section 9.1) |

---

*참고 문서: `docs_[리버트론]OpenArm(AA-K1)_User Manual_English.pdf`*
