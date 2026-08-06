# dora-openarm-webxr 데이터플로우 연동 및 실행 스크립트 모드화

- **작업 일자**: 2026-08-06
- **작업 분류**: Feature / Refactor

## 1. 개요 및 목적
- Quest 전용 UDP 수신 노드(`dora-openarm-quest-receiver`) 외에 WebXR 표준 수신 노드(`dora-openarm-webxr`)를 `dora_openarm_vr` 데이터플로우에 선택적으로 사용할 수 있도록 확장.
- 기존 Quest 수신 데이터플로우(`dataflow-*.yaml`)를 유지함과 동시에 `-webxr.yaml` 접미사(suffix)를 갖는 데이터플로우 파일 10종을 신규 생성.
- `scripts/run_*.sh` 실행 스크립트에서 기본값(default)을 `webxr`로 설정하고 인자(`quest` / `quest_receiver` / `webxr`)를 통해 수신 모드를 선택할 수 있도록 개편.

## 2. 주요 변경 사항
1. **`-webxr.yaml` 접미사 데이터플로우 파일 생성 (총 10종)**
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

2. **실행 스크립트 모드 지정 로직 개편 (`scripts/run_*.sh`)**
   - `scripts/run_real.sh`, `scripts/run_real_record.sh`, `scripts/run_real_prev_model.sh`, `scripts/run_sim.sh`, `scripts/run_sim_record.sh`
   - 기본 실행: `./scripts/run_real.sh` $\rightarrow$ WebXR 모드 (`-webxr.yaml`)
   - 인자 실행: `./scripts/run_real.sh quest` $\rightarrow$ Quest/UDP 모드 (`.yaml`)

3. **의존성 및 환경 수정**
   - `dora-openarm-kinematics/pyproject.toml`의 `requires-python` 요구사항을 Python 3.10 환경과 호환되도록 `>=3.10`으로 조정.
   - `dora-openarm-webxr` 패키지 설치 및 빌드 동기화 완료.

## 3. 테스트 및 승인 내용
- `dora build src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop-webxr.yaml` 검증 완료 (`Build finished successfully`).
- 사용자 최종 검토 및 승인 완료.
