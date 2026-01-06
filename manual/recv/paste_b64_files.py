#!/usr/bin/env python3
"""
Usage examples:

  # Restore files into an output directory (recommended)
  python paste_b64_files.py --out-dir "C:\\restore"
  python paste_b64_files.py --out-dir "/home/user/restore"

  # If you only send ONE file and want to force a single output file:
  python paste_b64_files.py --out "C:\\restore\\output.bin"
  python paste_b64_files.py --out "/home/user/restore/output.bin"

Controls:
  - Press Enter/any key to process the current clipboard content
  - Type 'q' (then Enter on non-Windows) to quit
"""

import argparse
import base64
import json
import sys
from pathlib import Path

MAGIC = b"J2B64v1\n"  # Must match sender


def read_clipboard_text() -> str:
    """
    Read clipboard text using OS-native tools:
      - Windows: powershell Get-Clipboard -Raw
      - macOS: pbpaste
      - Linux: xclip or xsel
    """
    if sys.platform.startswith("win"):
        import subprocess
        cmd = ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"Failed to read clipboard (powershell). {p.stderr.strip()}")
        return p.stdout

    if sys.platform == "darwin":
        import subprocess
        p = subprocess.run(["pbpaste"], capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError("Failed to read clipboard (pbpaste).")
        return p.stdout

    import subprocess
    for cmd in (["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True)
            if p.returncode == 0:
                return p.stdout
        except FileNotFoundError:
            continue

    raise RuntimeError("No clipboard tool found. Install xclip or xsel.")


def wait_for_keypress(prompt: str) -> str:
    print(prompt, end="", flush=True)
    if sys.platform.startswith("win"):
        import msvcrt
        ch = msvcrt.getch()
        try:
            return ch.decode("utf-8", errors="ignore")
        finally:
            print()
    else:
        return input()


def ensure_parent_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconstruct file(s) by decoding Base64 from clipboard on each key press."
    )
    parser.add_argument("--out-dir", default=None, help="Output directory to restore multiple files")
    parser.add_argument("--out", default=None, help="Force a single output file path (useful for one-file transfer)")
    parser.add_argument("--append", action="store_true", help="Append to existing file instead of truncating on START")
    args = parser.parse_args()

    if (args.out_dir is None) == (args.out is None):
        print("Error: specify exactly one of --out-dir or --out")
        return 1

    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else None
    out_file = Path(args.out).expanduser().resolve() if args.out else None

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {out_dir}")
    else:
        ensure_parent_dir(out_file)
        print(f"Output file: {out_file}")

    current_fp = None
    current_path = None
    total_written = 0

    print("Ready. Copy next Base64 payload to clipboard, then press a key here.")
    print("Press 'q' to quit.")
    print("-" * 70)

    while True:
        s = wait_for_keypress("Press key to process clipboard... ['q' to quit]: ")
        if s.strip().lower() == "q":
            print("Quit.")
            break

        try:
            text = read_clipboard_text().strip()
            if not text:
                print("Clipboard is empty.")
                continue

            decoded = base64.b64decode(text, validate=True)

        except Exception as e:
            print(f"Failed to decode Base64 from clipboard: {e}")
            continue

        # Control frame?
        if decoded.startswith(MAGIC):
            try:
                meta = json.loads(decoded[len(MAGIC):].decode("utf-8"))
                ftype = meta.get("type")
                fname = meta.get("name", "unknown")
            except Exception as e:
                print(f"Invalid control frame: {e}")
                continue

            if ftype == "start":
                # Close previous if still open
                if current_fp:
                    current_fp.close()
                    current_fp = None
                    current_path = None

                if out_file:
                    target = out_file
                else:
                    target = out_dir / Path(fname)

                ensure_parent_dir(target)
                mode = "ab" if args.append else "wb"
                current_fp = target.open(mode)
                current_path = target
                total_written = 0

                size = meta.get("size")
                print(f"[START] {fname} -> {target}")
                if size is not None:
                    print(f"  - Expected size: {size} bytes")
                continue

            if ftype == "end":
                if current_fp:
                    current_fp.close()
                    print(f"[END] {fname} -> {current_path} (written: {total_written} bytes)")
                    current_fp = None
                    current_path = None
                    total_written = 0
                else:
                    print(f"[END] {fname} (no open file)")
                continue

            print(f"Unknown control frame type: {ftype}")
            continue

        # Data frame
        if not current_fp:
            print("No open file. Send/Process a START frame first.")
            continue

        current_fp.write(decoded)
        current_fp.flush()
        total_written += len(decoded)
        print(f"[DATA] wrote {len(decoded)} bytes (total: {total_written} bytes) -> {current_path}")

    if current_fp:
        current_fp.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
