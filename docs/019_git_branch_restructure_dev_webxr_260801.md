# Git 브랜치 재구성 및 `dev_webxr` 브랜치 분기 작업

- **작업 일자**: 2026-08-07
- **작업 분류**: Refactor / Docs

## 1. 개요 및 목적
- `main` 브랜치를 이전 안정 커밋(`bb554862145a9296d6d1f2e8163c6dea62f773c4`) 위치로 되돌림(reset).
- 해당 커밋(`bb55486`) 기반으로 WebXR 기능 개발 관련 커밋(`fe79784` ~ `ba71d22`)이 포함된 `dev_webxr` 브랜치를 독립 분기 생성.
- 분기된 `dev_webxr` 브랜치 및 되돌려진 `main` 브랜치 상태를 원격 저장소(`origin`)에 동기화(push) 완료.

## 2. 주요 변경 사항
- **`.gitignore`**:
  - Obsidian 작업 환경 파일 무시 설정 (`.obsidian/`) 추가.
- **Git Branch 구조 변경**:
  - `dev_webxr` 브랜치 생성: `ba71d22f6c55e54454de850976b024d94ab0b0ee` (기존 WebXR/IK 기능 구현 최신 커밋 위치).
  - `main` 브랜치: `bb554862145a9296d6d1f2e8163c6dea62f773c4` 커밋으로 강제 되돌림(`reset --hard`).
  - `origin/main` 강제 푸시(`--force`) 및 `origin/dev_webxr` 신규 생성 푸시 반영 완료.

## 3. 테스트 및 승인 내용
- `main` 브랜치 커밋 히스토리 확인: `bb55486` 정상 가리킴.
- `dev_webxr` 브랜치 커밋 히스토리 확인: `ba71d22` 정상 가리킴.
- 원격 저장소(`origin`) 상태 확인: `origin/main`, `origin/dev_webxr` 정상 업데이트 완료.
