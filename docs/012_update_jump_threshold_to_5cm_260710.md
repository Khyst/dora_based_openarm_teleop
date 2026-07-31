# IK 점프 위험 차단선(JUMP_THRESHOLD_METERS) 5cm 조정

- **작업 일자**: 2026-07-31
- **작업 분류**: Config / Safety

## 1. 개요 및 목적
- VR 텔레옵 시 손 위치 유격 차단선(`JUMP_THRESHOLD_METERS`)을 기존 $8\text{cm}$ ($0.08\text{m}$)에서 **$5\text{cm}$ ($0.05\text{m}$)**로 더욱 보수적이고 안전하게 조정함.
- 차단 해제 및 IK 재개 시 남아있는 유격을 더욱 좁혀 복귀 시의 로봇 동작을 극도로 차분하고 안전하게 만듦.

## 2. 주요 변경 사항

- **수정 파일**: `src/nana_v3_dora_teleop_vr/dora-openarm-kinematics/src/dora_openarm_kinematics/ik.py`
- **구현 내용**:
  - `JUMP_THRESHOLD_METERS = 0.05` ($5\text{cm}$ 역치)
  - VR 손이 로봇 손 기준 $5\text{cm}$ 안쪽으로 접근해야 IK 재개 및 램핑 추종이 시작됨.

## 3. 테스트 및 승인 내용
- `./scripts/run_sim_play.sh` 파이프라인 연동 테스트 완료.
- 사용자 선택에 따른 $5\text{cm}$ 파라미터 업데이트 및 로컬 커밋 완료.
