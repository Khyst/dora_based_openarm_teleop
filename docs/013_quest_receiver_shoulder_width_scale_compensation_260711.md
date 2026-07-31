# VR 수신기 로봇 어깨 폭 스케일 보정(Scale Y Compensation) 구현

- **작업 일자**: 2026-07-31
- **작업 분류**: Feature / Scaling

## 1. 개요 및 목적
- 보정된 NANA v3 하드웨어 어깨 폭($36\text{cm}$)이 넓어지면서 조작자가 팔을 옆으로 벌렸을 때 로봇 팔 관절의 꺾임 각도가 전보다 시각적으로 덜 벌어지는 현상을 보정함.
- `quest_receiver.py`에 조작자 가슴 중심 대비 Y축(좌우 방향) 변위에 대한 **스케일 가중치 파라미터(`scale_y`, 기본값 1.15)**를 추가하여 이전 모델의 넓고 시원시원한 팔 벌림 감도를 재현함.

## 2. 주요 변경 사항

- **수정 파일**: `src/nana_v3_dora_teleop_vr/dora-openarm-vr/src/dora_openarm_vr/quest_receiver.py`
- **구현 내용**:
  1. **스케일 파라미터 CLI 옵션 추가**:
     - `--scale-y`: 좌우 팔 벌림 감도 가중치 (기본값: `1.15`, 15% 보정)
     - `--scale-x`: 전후 이동 가중치 (기본값: `1.0`)
     - `--scale-z`: 상하 이동 가중치 (기본값: `1.0`)
  2. **`QuestPoseProcessor` 변환 공식 반영**:
     ```python
     p_out[1] = FRAME_OFFSET_NECK[1] + (p_out[1] - FRAME_OFFSET_NECK[1]) * self.scale_y
     ```
  3. **안전성**:
     - 조작자가 손을 벌릴 때 어깨 너비 차이만큼 자연스럽게 $15\%$ 확장되어, 넓어진 로봇 어깨 기저점에서도 관절이 시원시원하게 바깥으로 벌어짐.

## 3. 테스트 및 승인 내용
- `./scripts/run_sim_play.sh` 파이프라인 연동 테스트 완료.
- 사용자 선택에 따른 스케일 가중치 옵션 추가 및 로컬 커밋 완료.
