# 커스텀 커스터마이징용 리서치 레포지토리 및 설명 문서 추가

- **작업 일자**: 2026-08-06
- **작업 분류**: Feature / Docs

## 1. 개요 및 목적
`dora_based_openarm_teleop` 커스터마이징 및 텔레오퍼레이션 기능 고도화를 위하여 외부 리서치 레포지토리 4종(`TeleVision`, `beavr-bot`, `openarmx_teleop_vr`, `xr_teleoperate`)과 추가 설명 문서(`013_vr_teleop_elbow_ik_enhancement_guide_260805.md`, `HL-IK.pdf`)를 로컬 및 원격 Git 저장소에 추가 통합합니다.
모든 리서치 레포지토리는 서브모듈(submodule) 방식이 아닌 일반 디렉터리 구조로 전체 소스코드가 포함되도록 관리합니다.

## 2. 주요 변경 사항
- **리서치 레포지토리 추가 (`src/researches/`)**:
  - `src/researches/TeleVision/`: TeleVision 기반 텔레오퍼레이션 제어 참조 소스
  - `src/researches/beavr-bot/`: BEAVR 로봇 텔레오퍼레이션 참조 소스
  - `src/researches/openarmx_teleop_vr/`: OpenARM VR 텔레오퍼레이션 브리지 소스
  - `src/researches/xr_teleoperate/`: XR 텔레오퍼레이션 프레임워크 참조 소스
  - *(각 레포지토리 내 `.git` 디렉터리 제거 완료하여 통째로 커밋)*
- **문서 추가 (`docs/`)**:
  - `docs/013_vr_teleop_elbow_ik_enhancement_guide_260805.md`: VR Teleop Elbow IK 개선 가이드 문서
  - `docs/HL-IK.pdf`: Humanoid Kinematics / IK 참조 문서

## 3. 테스트 및 승인 내용
- 각 레포지토리 내부 `.git` 디렉터리 유무 확인 완료 (서브모듈 등록 방지)
- `git status` 변경사항 점검 및 사용자 검토 승인 완료
- 원격 저장소(`origin/main`) 푸시 수행
