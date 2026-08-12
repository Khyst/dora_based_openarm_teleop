# Pandoc XeLaTeX 및 나눔글꼴 설정 가이드

- **작업 일자**: 2026-08-12
- **작업 분류**: Docs

## 1. 개요 및 목적
- Pandoc을 사용하여 마크다운 문서를 PDF로 변환 시 발생한 `XeLaTeX: Not installed` 오류 해결 및 한글 폰트 적용 설정 가이드 작성.
- Linux(Ubuntu) 환경에서 나눔글꼴(`NanumGothic`)을 적용하여 한글 PDF 문서를 정상 생성하도록 가이드 구성.

## 2. 주요 변경 사항
- **오류 분석**: Pandoc의 PDF 변환 백엔드 엔진인 `xelatex` 및 관련 TeX Live 패키지 미설치로 인한 문제 확인.
- **해결 방안 정리**:
  1. 필수 패키지 설치: `sudo apt update && sudo apt install -y texlive-xetex texlive-fonts-recommended texlive-plain-generic texlive-lang-korean fonts-nanum`
  2. CLI 사용 시: `pandoc input.md -o output.pdf --pdf-engine=xelatex -V mainfont="NanumGothic"`
  3. Obsidian Pandoc Plugin 사용 시: Extra PDF Arguments에 `-V mainfont="NanumGothic"` 추가
- **문서화**: `docs/025_pandoc_xelatex_nanum_font_setup_260814.md` 추가.

## 3. 테스트 및 승인 내용
- Pandoc XeLaTeX 설정 가이드 및 나눔글꼴 사용 파이프라인 사용자 승인 완료.
