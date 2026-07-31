# IK 구역 재진입 시 포즈 보간 및 속도 제한(Smooth Pose Ramping) 안전 가드

- **작업 일자**: 2026-07-31
- **작업 분류**: Feature / Safety Ramping

## 1. 개요 및 목적
- 8cm 차단 구역 밖에서 멈춰 있던 로봇 손이, VR 컨트롤러가 8cm 안쪽으로 들어오는 **IK 재개 시점(Re-entry Moment)**에 남아있던 $7.9\text{cm}$ 오차를 단 1개 프레임($0.02\text{초}$) 만에 도달하려 하면서 순간적으로 로봇이 "툭/울컥" 하고 빠르게 튀는 현상을 방지함.
- IK 재개 및 추종 시 **프레임당 최대 이동 거리(Step Limit)를 $6\text{mm}$ (최대 속도 $0.3\text{m/s}$)**로 제한하여 포즈 및 회전(Slerp)을 부드럽게 보간(Interpolation/Ramping)함.

## 2. 주요 변경 사항

- **수정 파일**: `src/nana_v3_dora_teleop_vr/dora-openarm-kinematics/src/dora_openarm_kinematics/ik.py`
- **구현 내용**:
  1. **Step Limit 파라미터 추가**: `MAX_STEP_METERS_PER_TICK = 0.006` ($20\text{ms}$ 틱당 max $6\text{mm}$, 초당 max $30\text{cm/s}$)
  2. **`_ramp_pose` 보간 함수 구현**:
     - 위치: $\Delta p = p_{vr} - p_{robot}$ 거리가 $6\text{mm}$ 이상이면 틱당 $6\text{mm}$씩 스무스하게 보간하여 쫓아감.
     - 회전: `scipy.spatial.transform.Slerp`를 통해 손목 Quaternion 회전도 비단결처럼 부드럽게 보간.
  3. **효과**:
     - $8\text{cm}$ 밖: 완벽 차단(Hold).
     - $8\text{cm}$ 안쪽 진입 순간: $7.9\text{cm}$ 오차가 있더라도 튀지 않고 초당 $30\text{cm/s}$의 부드러운 속도로 미끄러지듯 연결됨.
     - 오차 소멸 후: 50Hz 1:1 실시간 텔레옵 모드로 완전 전환되어 딜레이 없는 정밀 제어 제공.

## 3. 테스트 및 승인 내용
- `./scripts/run_sim_play.sh` 파이프라인 연동 테스트 완료.
- 사용자 요청에 따른 IK 재진입 램핑(Smooth Pose Ramping) 반영 및 커밋 완료.
