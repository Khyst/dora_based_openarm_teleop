# Quest Receiver Pose Processing Pipeline & Smoothing Guide

- **작업 일자**: 2026-07-30
- **작업 분류**: Docs

1. MetaQuest3에서 실제 Hardware Teleop를 안정적으로 하기 위한 좌표 변환 과정
2. Smoothing Logic for 안정성


## 1. 개요 및 목적
본 문서는 Meta Quest HMD 및 컨트롤러로부터 수신되는 원시(Raw) UDP 데이터 패킷이 로봇(OpenARM / MuJoCo) 제어를 위한 3D/8D 포즈 데이터로 변환되는 전체 파이프라인과 노이즈 제거를 위한 스무딩(One Euro Filter) 알고리즘의 동작 원리 및 파라미터 튜닝 가이드를 정리하는 것을 목적으로 합니다.

---

## 2. 데이터 처리 및 좌표계 변환 파이프라인 (Pipeline)

### 2.1 원시 데이터 수신 (Raw Packet Input)
UDP 소켓을 통해 JSON 형태로 수신되는 raw 패킷에는 다음과 같은 포즈 데이터가 포함되어 있습니다:
* **`rf` (Reference)**: 작업자의 HMD(헤드셋) 원시 포즈
* **`rc` (Right Controller)**: 오른손 컨트롤러 원시 포즈
* **`lc` (Left Controller)**: 왼손 컨트롤러 원시 포즈
* **데이터 포맷**: Unity 기준 위치(`x, y, z`) 및 쿼터니언 회전(`qx, qy, qz, qw`)

### 2.2 단계별 기준점(Frame of Reference) 변환 과정

```
[Unity 방 원점 (LH)] ➔ [오른손 좌표계 (RH)] ➔ [HMD(머리) 중심 상대 좌표계] ➔ [로봇 가슴 원점 (arm_origin)]
```

1. **오른손 좌표계 변환 (`parse_lh_to_rh`)**
   - Unity의 왼손 좌표계(LH: X-우, Y-상, Z-전)를 로봇 표준 오른손 좌표계(RH)로 변환: $Z \to -Z$, $q_x \to -q_x$, $q_y \to -q_y$.
2. **HMD 시점 중심 상대 좌표계 변환 (`active_p_ref`, `active_r_ref_inv`)**
   - 방 안에서의 절대 위치 및 헤드셋 회전(시선)에 독립적인 상대 위치/회전을 계산:
     $$\mathbf{p}_{\text{rel}} = \mathbf{R}_{\text{ref}}^{-1} \cdot (\mathbf{p}_{\text{ctrl}} - \mathbf{p}_{\text{ref}})$$
     $$\mathbf{r}_{\text{rel}} = \mathbf{R}_{\text{ref}}^{-1} \cdot \mathbf{r}_{\text{ctrl}}$$
   - 작업자가 고개를 돌리거나 서 있는 위치를 바꿔도 "머리 시선 기준" 손의 위치가 정렬됨.
3. **로봇 가슴 원점(`arm_origin`) 및 오프셋 적용 (`_R_FRAME`, `FRAME_OFFSET_NECK`, `r_fix`)**
   - VR 좌표 축을 로봇 좌표 축(X-전방, Y-좌측, Z-상방)으로 전환 (`_R_FRAME`)
   - HMD 위치에서 로봇 가슴 높이로 평행 이동 오프셋 적용 (`FRAME_OFFSET_NECK` = `[-0.085, 0, -0.14]`)
   - VR 컨트롤러 손잡이와 로봇 그리퍼 축 일치를 위한 90도 회전 보정 (`r_fix = Rot_z(90°)`)
     $$\mathbf{p}_{\text{out}} = \mathbf{R}_{\text{FRAME}} \cdot \mathbf{p}_{\text{rel}} + \text{FRAME\_OFFSET\_NECK}$$
     $$\mathbf{r}_{\text{out}} = \mathbf{R}_{\text{FRAME}} \cdot \mathbf{r}_{\text{rel}} \cdot \mathbf{r}_{\text{fix}}$$

---

## 3. 스무딩(Smoothing) 로직 및 파라미터 튜닝 가이드

### 3.1 1 Euro Filter (원유로 필터) 동작 원리
손떨림(노이즈) 억제와 빠른 이동 시 딜레이(Lag) 최소화를 동시에 만족하는 **적응형 저역통과 필터(Adaptive Low-Pass Filter)**입니다.

* **손이 천천히 움직이거나 멈춰 있을 때**: 차단 주파수($f_{\text{cutoff}}$)를 낮추어 손떨림 노이즈를 강력하게 보정.
* **손이 빠르게 움직일 때**: 속도($\text{speed}$)에 비례하여 차단 주파수를 높여 딜레이 없이 즉각 추종.

### 3.2 핵심 알고리즘 수식
$$\text{speed} = \|\mathbf{dp}_{\text{filtered}}\|$$
$$f_{\text{cutoff}} = \text{min\_cutoff} + \beta \cdot \text{speed}$$
$$\tau = \frac{1}{2\pi \cdot f_{\text{cutoff}}}, \quad \alpha = \frac{dt}{dt + \tau}$$
$$\mathbf{p}_{\text{filtered}} = \mathbf{p}_{\text{prev}} + \alpha \cdot (\mathbf{p}_{\text{raw}} - \mathbf{p}_{\text{prev}})$$
$$\mathbf{q}_{\text{filtered}} = \text{SLERP}(\mathbf{q}_{\text{prev}}, \mathbf{q}_{\text{raw}}, \alpha)$$

### 3.3 사용자 튜닝 파라미터 조절 가이드

| 파라미터 | 기본값 | 효과 및 조절 가이드 |
| :--- | :--- | :--- |
| **`min_cutoff`** | `2.0` | **[최소 차단 주파수 / 정지 시 노이즈 제거]**<br>• 값을 **낮추면** (예: `0.5 ~ 1.0`): 손이 멈춰 있을 때 로봇 손떨림이 현저히 줄어들고 매우 안정적입니다.<br>• 값을 **높이면** (예: `5.0 ~ 10.0`): 미세한 움직임에도 즉각 반응하지만 떨림이 전달될 수 있습니다. |
| **`beta`** | `0.04` | **[속도 반응 계수 / 빠른 이동 시 딜레이 제거]**<br>• 값을 **높이면** (예: `0.1 ~ 0.5`): 빠른 손 동작 시 딜레이(Lag)가 거의 사라져 반응속도가 극대화됩니다.<br>• 값을 **낮추면** (예: `0.001`): 빠른 동작 중에도 부드러움이 유지되나 약간의 추종 지연이 발생할 수 있습니다. |
| **`d_cutoff`** | `1.5` | **[속도 필터 차단 주파수 / 튀는 노이즈 감쇄]**<br>• 미분 속도($\mathbf{dp}$)의 튀는 성분을 1차 차단합니다. 기본값(`1.0 ~ 2.0`) 유지를 권장합니다. |

### 3.4 추적 손실 대응: `smoother.reset()`
* VR 센서 카메라 가림 등으로 추적 유효성이 `INVALID`가 된 후 복구되는 순간, `smoother.reset()`을 호출하여 과거 필터 히스토리를 초기화합니다.
* 이를 통해 **추적 재개 시 과거 위치로 인해 로봇 손이 튀거나 지연되는 현상(Jump/Lag)을 방지**합니다.

---

## 4. 최종 출력 데이터 구조 및 메타데이터

### 4.1 최종 8차원 포즈 데이터 (`pose_with_gripper`)
위치(3D) + 회전 쿼터니언(4D, Scalar-First) + 그리퍼 각도(1D)로 결합되어 전송됩니다:
$$\mathbf{Pose}_{\text{final}} = [x, y, z, q_w, q_x, q_y, q_z, \text{gripper\_angle}]$$
* **$q_w, q_x, q_y, q_z$**: MuJoCo / ROS2 표준인 **Scalar-First 쿼터니언** 형식
* **`gripper_angle`**: VR 트리거/그립 압력($0.0 \sim 1.0$)을 로봇 그리퍼 라디안 각도 범위로 선형 매핑

### 4.2 메타데이터 타임스탬프 (`ts`) 전송 이유
`node.send_output(channel, data, ts)` 형태로 나노초 타임스탬프(`ts = {"timestamp": time.time_ns()}`)를 동시 전송하는 목적:
1. **Dora 데이터플로우 동기화**: IK, 뷰어, 드라이버 노드가 동일한 시간대 데이터를 동기식으로 결합 처리.
2. **지연 시간(Latency) 측정**: VR 생성 ➔ 데이터 변환 ➔ 로봇 구동까지의 전 과정을 모니터링하여 통신 병목 진단.
3. **시계열 AI 데이터 수집**: 텔레오퍼레이션 데이터셋 수집 시 정확한 고정밀 시간축 기록.

---

## 5. 테스트 및 승인 내용
- **검증 방식**: `quest_receiver.py` 파이프라인 코드 수식 및 주석 분석 완료.
- **결과**: HMD-상대 좌표계 변환, 1 Euro Filter 수식 체계 및 사용자 조정용 파라미터 가이드 작성 완료.
