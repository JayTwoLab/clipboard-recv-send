# clipboard-recv-send

[English README](README.md)

## 개요

- `clipboard-recv-send`는 윈도우 환경에서 클립보드를 통해 바이너리 파일(예: 실행 파일, 이미지 등)을 base64로 인코딩하여 송수신할 수 있도록 하는 Python 스크립트 모음입니다. 
- 네트워크나 USB 없이도 클립보드만으로 파일을 전송할 수 있습니다.

<br />

## 구성

- `sender/clip_b64_send_win.py`: 파일을 base64로 인코딩하여 클립보드에 순차적으로 복사하는 송신 스크립트
- `receiver/clip_b64_recv_poll_win.py`: 클립보드를 주기적으로 감시(polling)하여 base64 데이터를 복호화해 파일로 저장하는 수신 스크립트
- 각 폴더의 `run.cmd`: 실행 예시를 위한 커맨드 파일

<br />

## 동작 원리

- (1) 송신 스크립트(sender)는 지정한 파일을 base64로 인코딩하여 일정 크기(chunk)로 나누고, 각 청크를 클립보드에 복사합니다.
- (2) 수신 스크립트(receiver)는 클립보드를 주기적으로 확인하여, 올바른 형식의 base64 청크를 감지하면 순서대로 파일로 복원합니다.
- (3) 각 청크에는 순서, 전체 청크 수, CRC32, 파일명, 파일 크기 등의 메타데이터가 포함되어 있어 무결성 및 순서 보장이 가능합니다.

<br />

---

## 사용법

### 1. 송신 (Sender)

```bat
cd sender
python clip_b64_send_win.py <보낼파일> --chunk 1m --interval 10
```

- 예시:

```bat
python clip_b64_send_win.py npp.8.8.1.Installer.x64.exe --chunk 1m --interval 10
```

- 옵션:
   - `--chunk`: base64 페이로드 청크 크기(기본 4m, 예: 1m, 512k 등)
   - `--interval`: 각 청크를 클립보드에 복사하는 간격(초)

<br />

---

### 2. 수신 (Receiver)

```bat
cd receiver
python clip_b64_recv_poll_win.py <복원할파일명> --interval 2
```

- 예시:

```bat
python clip_b64_recv_poll_win.py restored.bin --interval 2
```

옵션:
- `--interval`: 클립보드 감시 주기(초)
- `--timeout`: 지정 시간 동안 진행이 없으면 중단(0=무제한)
- `--append`: 기존 파일에 이어쓰기
- `--expect-total`: 예상 청크 수 강제 지정

<br />

## 주의사항

- **윈도우 환경에서만 동작합니다.**
- 클립보드에 다른 내용이 복사되면 전송이 중단될 수 있습니다.
- 대용량 파일은 전송에 시간이 오래 걸릴 수 있습니다.
- 송수신 PC의 시간 동기화 및 사용자 조작에 주의하세요.

<br />

## 예시 시나리오

- (1) 수신 측 `cd receiver && run.cmd` 또는 위 명령어로 복원 대기.  **반드시 수신 측을 먼저 실행하여야 합다.**
- (2) 송신 측 `cd sender && run.cmd` 또는 위 명령어로 파일을 클립보드로 전송 시작합니다.
- (3) 클립보드를 통해 파일이 순차적으로 복원됩니다.

<br />

## 라이선스

- MIT License

