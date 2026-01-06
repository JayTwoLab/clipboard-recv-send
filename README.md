# clipboard-recv-send

클립보드와 파일 간의 데이터 송수신을 자동/수동으로 지원하는 도구 모음입니다.

## 개요
이 프로젝트는 윈도우 환경에서 클립보드와 파일 간에 base64 인코딩을 활용하여 데이터를 송수신할 수 있도록 도와줍니다. 자동화 스크립트와 수동 스크립트가 모두 제공되어 다양한 상황에서 활용할 수 있습니다.

## 디렉터리 구조

- `automatic/` : 자동화된 송수신 스크립트
  - `sender/clip_b64_send_win.py` : 파일을 base64로 인코딩하여 클립보드에 복사
  - `receiver/clip_b64_recv_poll_win.py` : 클립보드의 base64 데이터를 주기적으로 감시하여 파일로 저장
  - 각 디렉터리별 `run.cmd` : 실행을 위한 배치 파일
- `manual/` : 수동 송수신 스크립트
  - `sender/copy_b64_files.py` : 파일을 base64로 인코딩하여 클립보드에 복사
  - `recv/paste_b64_files.py` : 클립보드의 base64 데이터를 파일로 저장

## 사용법

### 자동 모드
- 자동 송신: `automatic/sender/clip_b64_send_win.py` 실행
- 자동 수신: `automatic/receiver/clip_b64_recv_poll_win.py` 실행
- 각 폴더의 `run.cmd`로도 실행 가능

### 수동 모드
- 파일 복사: `manual/sender/copy_b64_files.py <파일경로>`
- 파일 붙여넣기: `manual/recv/paste_b64_files.py <저장할_디렉터리>`

## 특징
- base64 인코딩을 사용하여 바이너리 파일도 안전하게 송수신 가능
- 윈도우 환경에 최적화
- 파이썬 3 필요

## 라이선스
MIT 라이선스

## 참고
각 하위 폴더의 README.md를 참고하세요.