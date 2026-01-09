# clipboard-recv-send

[Korean README](README.ko.md)

## Overview

- `clipboard-recv-send` is a collection of Python scripts that allow you to send and receive binary files (e.g., executables, images) via the clipboard in Windows environments, using base64 encoding.
- You can transfer files using only the clipboard, without network or USB.

<br />

## Structure

- `sender/clip_b64_send_win.py`: Script to encode a file as base64 and copy it to the clipboard in sequence
- `receiver/clip_b64_recv_poll_win.py`: Script to poll the clipboard, decode base64 data, and save it as a file
- `run.cmd` in each folder: Command file for example execution

<br />

## How It Works

- (1) The sender script encodes the specified file as base64, splits it into chunks, and copies each chunk to the clipboard.
- (2) The receiver script periodically checks the clipboard, detects valid base64 chunks, and restores the file in order.
- (3) Each chunk includes metadata such as order, total chunk count, CRC32, filename, and file size to ensure integrity and correct sequence.

<br />

---

## Usage

### 1. Sending (Sender)

```bat
cd sender
python clip_b64_send_win.py <file_to_send> --chunk 1m --interval 10
```

- Example:

```bat
python clip_b64_send_win.py npp.8.8.1.Installer.x64.exe --chunk 1m --interval 10
```

- Options:
	- `--chunk`: base64 payload chunk size (default 4m, e.g., 1m, 512k)
	- `--interval`: interval (seconds) between copying each chunk to the clipboard

<br />

---

### 2. Receiving (Receiver)

```bat
cd receiver
python clip_b64_recv_poll_win.py <output_filename> --interval 2
```

- Example:

```bat
python clip_b64_recv_poll_win.py restored.bin --interval 2
```

Options:
- `--interval`: clipboard polling interval (seconds)
- `--timeout`: stop if no progress for specified time (0=unlimited)
- `--append`: append to existing file
- `--expect-total`: force expected chunk count

<br />

## Notes

- **Works only on Windows.**
- If other content is copied to the clipboard, transfer may be interrupted.
- Large files may take a long time to transfer.
- Pay attention to time synchronization and user actions on both sender and receiver PCs.

<br />

## Example Scenario

- (1) On the receiver side, run `cd receiver && run.cmd` or the above command to wait for restoration. **Always start the receiver first.**
- (2) On the sender side, run `cd sender && run.cmd` or the above command to start sending the file to the clipboard.
- (3) The file will be restored sequentially via the clipboard.

<br />

## License

- MIT License
