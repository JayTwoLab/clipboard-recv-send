# clipboard-recv-send

[Korean README](README.ko.md)

This project provides tools for sending and receiving clipboard data between devices, supporting both automatic and manual methods. It is designed for Windows environments and uses base64 encoding for clipboard content transfer.

## Structure

- `automatic/`
  - `receiver/`: Automatically receives clipboard data.
  - `sender/`: Automatically sends clipboard data.
- `manual/`
  - `recv/`: Manually receives clipboard data.
  - `sender/`: Manually sends clipboard data.

## Features

- **Automatic Mode**: Continuously monitors and transfers clipboard data.
- **Manual Mode**: Allows manual selection and transfer of clipboard files.
- **Base64 Encoding**: Ensures safe transfer of clipboard content.
- **Windows Support**: Scripts and commands are tailored for Windows systems.

## Usage

### Automatic Mode

1. Go to the `automatic/receiver/` or `automatic/sender/` directory.
2. Run the provided scripts (`clip_b64_recv_poll_win.py` or `clip_b64_send_win.py`).
3. Use the `run.cmd` files for quick execution.

### Manual Mode

1. Go to the `manual/recv/` or `manual/sender/` directory.
2. Use the scripts (`paste_b64_files.py` or `copy_b64_files.py`) to manually transfer clipboard files.

## License

See the [LICENSE](LICENSE) file for details.

## Author

Developed by JayTwoLab.
