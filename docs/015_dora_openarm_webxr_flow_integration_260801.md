# dora-openarm-webxr 데이터플로우 연동 및 인증서 자동화

- **작업 일자**: 2026-08-06
- **작업 분류**: Feature / Refactor / Fix

## 1. 개요 및 목적
- Quest 전용 UDP 수신 노드(`dora-openarm-quest-receiver`) 외에 WebXR 표준 수신 노드(`dora-openarm-webxr`)를 `dora_openarm_vr` 데이터플로우에 선택적으로 사용할 수 있도록 확장.
- 기존 Quest 수신 데이터플로우(`dataflow-*.yaml`)를 유지함과 동시에 `-webxr.yaml` 접미사(suffix)를 갖는 데이터플로우 파일 10종을 신규 생성.
- `dora-openarm-webxr` 실행 시 필요한 TLS 인증서/키(`server.crt`, `server.key`)를 YAML 노드의 `env` 및 `scripts/run_*.sh` 환경변수로 기본값 설정하여 자동 발급 및 경로 연동 보완.

## 2. 주요 변경 사항
1. **TLS 인증서 기본 설정 연동**
   - `dora-openarm-webxr` 레포지토리 내 저장된 인증서 경로 (`dora-openarm-webxr/example/server.crt`, `server.key`)를 YAML 환경변수 및 실행 스크립트에 기본값으로 설정:
     ```yaml
     env:
       TLS_CERTIFICATE_FILE: "../../dora-openarm-webxr/example/server.crt"
       TLS_KEY_FILE: "../../dora-openarm-webxr/example/server.key"
     ```

2. **`-webxr.yaml` 접미사 데이터플로우 파일 생성 (총 10종)**
   - `dora-openarm-vr/config/dataflow-nana-teleop-webxr.yaml`
   - `dora-openarm-vr/config/dataflow-nana-teleop-sim-webxr.yaml`
   - `dora-openarm-vr/config/dataflow-mujoco-webxr.yaml`
   - `dora-openarm-vr/config/dataflow-data-collection-webxr.yaml`
   - `dora-openarm-vr/config/dataflow-mujoco-data-collection-webxr.yaml`
   - `dora-openarm-vr/config/dataflow-nana-teleop-data-collection-webxr.yaml`
   - `dora-openarm-vr/config/dataflow-nana-teleop-sim-data-collection-webxr.yaml`
   - `dora-openarm-vr/config/dataflow-nana-teleop-record-webxr.yaml`
   - `dora-openarm-vr/config/dataflow-nana-teleop-sim-record-webxr.yaml`
   - `dora-openarm-vr/config/dataflow-nana-teleop-prev-model-webxr.yaml`

3. **실행 스크립트 모드 지정 로직 개편 (`scripts/run_*.sh`)**
   - `scripts/run_real.sh`, `scripts/run_real_record.sh`, `scripts/run_real_prev_model.sh`, `scripts/run_sim.sh`, `scripts/run_sim_record.sh`
   - 기본 실행: `./scripts/run_real.sh` $\rightarrow$ WebXR 모드 (`-webxr.yaml`) + TLS 환경변수 자동 지정
   - 인자 실행: `./scripts/run_real.sh quest` $\rightarrow$ Quest/UDP 모드 (`.yaml`)

## 3. 테스트 및 승인 내용
- `dora build src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop-webxr.yaml` 검증 완료 (`Build finished successfully`).
- 인증서 인자 누락 에러(ExitCode 2) 해결 및 사용자 최종 검토 승인 완료.
