# VR 텔레옵 위치 급변 방지 차단 및 안전 구역 재진입 가드 (Drop & Safety Re-entry Guard)

- **작업 일자**: 2026-07-31
- **작업 분류**: Feature / Safety

## 1. 개요 및 목적
- Meta Quest 3 VR 텔레옵 시 트래킹 상실 후 복귀, Grip 버튼 재개, 또는 VR 손 위치의 순간적인 점프(Jump) 시 로봇 팔이 급격하게 돌아가는(급발진) 현상을 사전 차단함.
- IK 목표 위치 변화량이 안전 역치를 초과할 경우 IK 연산 및 로봇 관절 명령을 일시 **차단(Drop/Freeze)**하고, 조작자가 VR 손을 로봇 손 근처로 **다시 가까이 가져와 안전 범위 내로 재진입(Safety Re-entry)할 때 텔레옵이 안전하게 재개**되도록 안전 가드를 구축함.

## 2. 주요 변경 사항

### 2.1 IK 노드 안전 가드 로직 구현 (`dora-openarm-kinematics`)
- **수정 파일**: `src/nana_v3_dora_teleop_vr/dora-openarm-kinematics/src/dora_openarm_kinematics/ik.py`
- **구현 내용**:
  1. **3D Jump Threshold 설정**: `JUMP_THRESHOLD_METERS = 0.08` ($8\text{cm}$ 안전 기준 거리)
  2. **위험 감지 및 차단**:
     - 새 포즈 수신 시 이전 목표 위치와의 3D 거리 $|\Delta P| = \|P_{new} - P_{last}\|$ 계산.
     - $|\Delta P| > 8\text{cm}$ 발생 시 차단 상태(`engage_blocked = True`)로 전환하고 IK 목표 업데이트 스킵 및 안내 콘솔 출력:
       `[IK Safety Guard] RIGHT arm target jump detected (15.2 cm > 8.0 cm). Holding robot pose. Move VR hand closer to resume.`
  3. **안전 구역 재진입 시 자동 복구**:
     - 조작자가 VR 손을 로봇 손 기준 $8\text{cm}$ 이내로 가까이 접근시키면 (`dist <= 8.0cm`):
     - `engage_blocked = False`로 복구되고 텔레옵이 점프 없이 부드럽게 재개됨.

## 3. 테스트 및 승인 내용
- `./scripts/run_sim_play.sh`를 통한 dora 파이프라인 연동 및 정상 동작 검증 완료.
- 사용자 요청 1번 방식(Drop & Safety Re-entry) 적용 완료.
