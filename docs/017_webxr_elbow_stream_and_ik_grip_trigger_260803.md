# WebXR Elbow 스트림 수신 확인 및 IK 시작 트리거 grip_left/right 지정

- **작업 일자**: 2026-08-06
- **작업 분류**: Feature / Fix

## 1. 개요 및 목적
- WebXR 수신 시 `elbow` 데이터가 실제로 수신되는지 터미널 콘솔 로그를 통해 실시간으로 명확히 인지/확인할 수 있도록 로깅 기능 추가.
- IK Solver(`dora-openarm-kinematics`) 노드의 타겟 추적 시작 트리거를 기존 `trigger` 입력에서 `grip_left`, `grip_right` 입력으로 변경 설정하여 WebXR Squeeze(Grip) 버튼과 IK 시작/해제 동작을 정확히 매핑.

## 2. 주요 변경 사항
1. **WebXR 노드 (`dora-openarm-webxr/main.py`) 수신 검증 디버그 출력**
   - `elbow_right`, `elbow_left` 데이터 수신 시 콘솔에 스트리밍 상태 및 위치 좌표(`pos: (x, y, z)`)를 실시간으로 인쇄하는 로깅 코드 추가:
     ```python
     if time.perf_counter() % 1.0 < 0.05:
         print(f"[webxr] {elbow} stream active -> pos: ({adjusted_elbow[0]:.3f}, {adjusted_elbow[1]:.3f}, {adjusted_elbow[2]:.3f})")
     ```

2. **WebXR 데이터플로우 YAML 10종의 `ik` 노드 시작 트리거 변경**
   - `ik` 노드의 `inputs`에서 기존 `trigger_right`/`trigger_left` 매핑 대신 `grip_right: webxr/grip_right` 및 `grip_left: webxr/grip_left`를 사용하여 IK 추적 활성화(시작) 조건 지정.

## 3. 테스트 및 승인 내용
- `dora build src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop-webxr.yaml` 정상 빌드 성공 (`Build finished successfully`).
- 사용자 최종 검토 및 승인 완료.
