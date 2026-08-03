# Quest 3 Teleop IK 파라미터 튜닝 체크리스트 (어깨 Joint1 구동 개선)

- **작업 일자**: 2026-08-03
- **작업 분류**: Docs

## 1. 개요 및 목적
Quest 3 VR 컨트롤러 기반 텔레오퍼레이션(Teleop) 수행 시 로봇 어깨(Joint 1) 관절의 구동 제약 및 반응성 문제를 해결하기 위해, IK(Inverse Kinematics) 솔버의 파라미터 튜닝 체크리스트 및 가이드를 문서화합니다.

## 2. 주요 파라미터 튜닝 가이드

### 1. 안전 제약 (Safety & Limits)
- `--limit-velocity` (기본값: `False` / 플래그 명시 필요)
  - **역할**: 관절별 최대 속도 제한(Caps)을 QP 제약 조건에 강제로 주입합니다.
  - **튜닝 가이드**: 실물 로봇 제어 시 반드시 명시(`--limit-velocity`)하여 VR 컨트롤러 급가속이나 특이점 튐 현상으로부터 모터 파손을 방지합니다.

### 2. 관절 구동 및 자세 억제 (Posture & Workspace)
- `--posture-cost` (기본값: `0.01`)
  - **역할**: 기본 중립 자세(Home Pose)로 돌아가려는 가중치입니다.
  - **튜닝 가이드**:
    - 어깨 관절이 잘 움직이지 않거나 묶여 있는 현상이 발생할 때 `0.001` 또는 `0.0`으로 대폭 낮추면 어깨 관절 구동이 활성화됩니다.
    - 팔꿈치가 어색하게 꺾이면 `0.05 ~ 0.1`로 올려 사람다운 자세를 유지하도록 유도합니다.

### 3. 목표 추종 우선순위 (Position vs Orientation)
- `--pos-cost` (기본값: `1.0`) / `--ori-cost` (기본값: `1.0`)
  - **역할**: 손끝 위치 오차($X, Y, Z$)와 회전 오차(Orientation) 추종 간의 가중치 비율을 설정합니다.
  - **튜닝 가이드**: 어깨 동작 반응성을 높이고 싶다면 `--pos-cost 5.0 ~ 10.0`으로 상향하여, 회전각보다 손끝 위치 추종을 최우선으로 풀도록 유도합니다.

### 4. 연산 수렴성 및 반응성 (Convergence & Responsiveness)
- `--max-iters` (기본값: `5`)
  - **역할**: 이벤트(Tick) 당 QP 최적화를 수행하는 최대 반복 연산 횟수입니다.
  - **튜닝 가이드**:
    - 기본값 5는 어깨 등 베이스 관절까지 IK 오차가 역전파되기에 부족할 수 있으므로 `15 ~ 25`로 상향하여 수렴 정확도를 제고합니다.
    - 추종 반응이 둔하면 높이고, CPU 연산 오버헤드가 크면 낮춥니다.

### 5. 특이점 및 떨림 방어 (Damping & Regularization)
- `--lm-damping` (기본값: `0.01`)
  - **역할**: Levenberg-Marquardt 감쇄 값으로, 팔이 완전히 펴지는 특이점(Singularity) 부근에서 관절 속도가 발산하는 것을 막아줍니다.
  - **튜닝 가이드**: 팔이 쫙 펴질 때 솔버가 거칠게 튀면 `0.1 ~ 0.3`으로 상향합니다.
- `--damping` (기본값: `0.25`)
  - **역할**: 전체적인 관절 속도 정규화(Smoothing) 파라미터입니다.
  - **튜닝 가이드**: 손을 고정하고 있을 때 미세한 노이즈로 로봇이 덜덜거리면 `1.0 ~ 2.0`으로 올려 움직임을 부드럽게 다듬습니다.

## 3. 권장 Dataflow YAML 파라미터 조합 (어깨 구동 + 안전 모드)

```yaml
# dataflow-nana-teleop.yaml 적용 예시
  - id: ik
    build: pip install -e ../../dora-openarm-kinematics
    path: dora-openarm-ik
    args: >-
      --xml ../../../nana_v3_description/assets/robot/urdf/nana_v3.xml
      --mode bimanual
      --limit-velocity
      --posture-cost 0.001
      --pos-cost 5.0
      --max-iters 20
      --lm-damping 0.1
      --damping 1.0
      --dt 0.02
```

## 4. 테스트 및 승인 내용
- Quest 3 기반 Teleop 환경에서 어깨 관절(Joint1) 구동 반응성 및 안정성 확보를 위한 IK 파라미터 가이드 검토 및 작성 완료.
