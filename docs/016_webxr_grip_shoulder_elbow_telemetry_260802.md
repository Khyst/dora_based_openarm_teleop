# WebXR 컨트롤러 Grip 및 Shoulder/Elbow 관절 데이터 수신 확장

- **작업 일자**: 2026-08-06
- **작업 분류**: Feature

## 1. 개요 및 목적
- WebXR 기반 VR Teleop 구동 시 컨트롤러의 Grip(Squeeze) 입력값(`grip_left`, `grip_right`)과 연산된 어깨/팔꿈치 관절 데이터(`shoulder_left`, `shoulder_right`, `elbow_left`, `elbow_right`)를 실시간으로 수신 및 전송할 수 있도록 확장.
- 기존 Quest 3 하드웨어 컨트롤러의 `buttons[1]` (Grip/Squeeze) 입력과 HMD/컨트롤러 상대 위치 기반 2-Link Arm Kinematic 기하 모델을 연동하여 ik 및 downstream 노드로 제공.

## 2. 주요 변경 사항
1. **WebXR Client (`ar.js`) 데이터 추출 구현**
   - `gamepad.buttons[1]` 입력값 추출 및 `grip_left`, `grip_right` 전송 추가.
   - HMD Pose (`getViewerPose`)와 Controller Pose 간 상대 기하학 연산을 통한 `shoulder_left/right` 및 `elbow_left/right` 포즈 계산/전송 로직 구현.
   - `hand-tracking` optional feature 지원 추가.

2. **WebXR Server Node (`dora-openarm-webxr/main.py`) 노드 파이프라인 확장**
   - WebSocket 수신 시 `grip_left`, `grip_right`, `shoulder_left`, `shoulder_right`, `elbow_left`, `elbow_right` 파싱 및 dora 노드 output 추가.
   - `grip` 입력값을 반영한 `pose_right`, `pose_left` 내 `gripper_angle` 매핑 결합 보완.

3. **WebXR Dataflow YAML (`config/dataflow-*-webxr.yaml`) 10종 노드 output 확장**
   - `webxr` 노드의 `outputs` 항목에 `grip_right`, `grip_left`, `shoulder_right`, `shoulder_left`, `elbow_right`, `elbow_left`, `pose_reference` 추가 반영.

## 3. 테스트 및 승인 내용
- `dora build src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop-webxr.yaml` 검증 완료 (`Build finished successfully`).
- 사용자 최종 검토 및 승인 완료.
