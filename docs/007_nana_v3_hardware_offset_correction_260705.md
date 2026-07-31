# NANA v3 실측 하드웨어 오프셋 보정 및 모델 반영

- **작업 일자**: 2026-07-31
- **작업 분류**: Fix / Refactor

## 1. 개요 및 목적
- 실제 하드웨어에 장착된 NANA v3 로봇의 양팔(Left/Right Arm) 마운팅 오프셋 수치(xyz/pos)를 URDF 및 MuJoCo XML에 정밀 반영함.
- 기존 모델(`nana_v3.urdf`, `nana_v3.xml`)과 실제 하드웨어 간의 마운팅 위치 차이로 발생하는 VR 텔레옵 IK 및 관절 각도 산출 오차를 보정하기 위함.

## 2. 주요 변경 사항

### 2.1 신규 보정 모델 파일 생성 (`nana_v3_corrected.urdf`, `nana_v3_corrected.xml`)
- **생성 위치**: 
  - `src/nana_v3_description/assets/robot/urdf/`
  - `src/nana_v3_description/urdf/`
- **수정 반영 수치**:
  1. **왼팔 (left_link0 / left_link1)**:
     - URDF (`nana_v3_left_nana_v3_body_link0_joint`): `xyz="0.0 0.18 1.22"`
     - MuJoCo XML (`nana_v3_left_link0_collision` geom): `pos="0 0.18 1.22"`
     - MuJoCo XML (`nana_v3_left_link1` body): `pos="0 0.2425 1.22"` (`link0` 오프셋 $0.18$ + joint1 y축 오프셋 $0.0625$ 연동)
  2. **오른팔 (right_link0 / right_link1)**:
     - URDF (`nana_v3_right_nana_v3_body_link0_joint`): `xyz="0.0 -0.18 1.22"`
     - MuJoCo XML (`nana_v3_right_link0_collision` geom): `pos="0 -0.18 1.22"`
     - MuJoCo XML (`nana_v3_right_link1` body): `pos="0 -0.2425 1.22"` (`link0` 오프셋 $-0.18$ + joint1 y축 오프셋 $-0.0625$ 연동)
  3. **Teleop 기준점 (`arm_origin` site)**:
     - MuJoCo XML (`arm_origin` site): `pos="0 0 1.22"`

### 2.2 Dora Dataflow YAML 설정 파일 모델 경로 일괄 업데이트
- **대상 파일 (총 8개)**:
  - `dataflow-nana-teleop.yaml`
  - `dataflow-nana-teleop-sim.yaml`
  - `dataflow-nana-teleop-play.yaml`
  - `dataflow-nana-teleop-sim-play.yaml`
  - `dataflow-nana-teleop-record.yaml`
  - `dataflow-nana-teleop-sim-record.yaml`
  - `dataflow-nana-teleop-data-collection.yaml`
  - `dataflow-nana-teleop-sim-data-collection.yaml`
- **수정 내용**: `ik` 및 `mujoco-viewer` 노드의 `--xml` 인자 경로를 `nana_v3_corrected.xml`로 변경하여 `run_sim_play.sh` 등 스크립트 실행 시 신규 오프셋 모델이 자동 적용되도록 반영.

## 3. 테스트 및 승인 내용
- MuJoCo Python API를 통한 XML 파싱 유효성 테스트 검증 완료 (`body count: 17`).
- 사용자 검토 및 최종 승인 완료.
