# clipboard-recv-send

[Korean README](README.ko.md)

This project is a collection of Python scripts that allow you to safely send and receive binary files (such as executables and images) via the clipboard in Windows environments, without using network or USB. All file transfers use base64 encoding.

## Key Features

- **Automatic Mode**: Continuously monitors the clipboard to automatically send and receive files.
- **Manual Mode**: Allows users to manually select files to copy to or paste from the clipboard.
- **Base64 Encoding**: Ensures safe transfer of clipboard data.
- **Windows Support**: All scripts and commands are designed for Windows environments.

## Folder Structure

- `automatic/`
	- `sender/clip_b64_send_win.py`: Script to encode files as base64 and copy them to the clipboard sequentially
	- `receiver/clip_b64_recv_poll_win.py`: Script to periodically check the clipboard and restore files from base64 data
	- `run.cmd` in each folder: Command file for example execution
- `manual/`
	- `sender/copy_b64_files.py`: Copy multiple files to the clipboard as base64
	- `recv/paste_b64_files.py`: Save base64 data from the clipboard as files

## Usage

### Automatic Mode

1. Go to the `automatic/sender/` or `automatic/receiver/` folder.
2. Run the corresponding script (`clip_b64_send_win.py` or `clip_b64_recv_poll_win.py`).
3. You can use the `run.cmd` file for quick execution.

### Manual Mode

1. Go to the `manual/sender/` or `manual/recv/` folder.
2. Run the scripts as follows:

#### Copy files (sender)
```bash
python copy_b64_files.py <file_path>
```
- You can copy multiple files at once.

#### Paste files (recv)
```bash
python paste_b64_files.py <target_directory>
```
- You can paste multiple files at once.

## How It Works

1. The sender script encodes the specified file as base64 and copies it to the clipboard in chunks.
2. The receiver script periodically checks the clipboard, detects base64 chunks, and restores the file.
3. Each chunk includes metadata such as order, total chunk count, CRC32, filename, and file size to ensure integrity and correct sequence.

## Notes

- Python 3 is required.
- This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---
