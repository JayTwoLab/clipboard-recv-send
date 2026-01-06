#!/usr/bin/env python3
"""
Usage examples:

  # Send all files in a directory (sorted by file name), chunked Base64 to clipboard
  python copy_b64_files.py "C:\\path\\to\\dir"
  python copy_b64_files.py "/home/user/data"

  # Include subdirectories
  python copy_b64_files.py "/home/user/data" --recursive

  # Only specific extensions
  python copy_b64_files.py "/home/user/data" --extensions .txt .bin

  # Set Base64 chunk size in KB (minimum: 1KB). Default: 1024KB
  python copy_b64_files.py "/home/user/data" --b64-chunk-kb 4

Protocol notes:
  - Every clipboard payload is Base64 text.
  - Decoded bytes are either:
      (A) a control frame: starts with MAGIC then JSON
      (B) raw file bytes (data frame), written as-is by receiver
"""

import argparse
import base64
import json
import sys
import time
from pathlib import Path

MAGIC = b"J2B64v1\n"  # Must match receiver


def human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    for u in units:
        if f < 1024.0 or u == units[-1]:
            return f"{f:.2f} {u}" if u != "B" else f"{int(f)} {u}"
        f /= 1024.0
    return f"{n} B"


def list_files_sorted(dir_path: Path, recursive: bool) -> list[Path]:
    if recursive:
        files = [p for p in dir_path.rglob("*") if p.is_file()]
    else:
        files = [p for p in dir_path.iterdir() if p.is_file()]

    files.sort(key=lambda p: (p.name.lower(), str(p).lower()))
    return files


def copy_to_clipboard(text: str) -> None:
    """
    Copy text to clipboard using OS-native tools:
      - Windows: clip
      - macOS: pbcopy
      - Linux: xclip or xsel
    """
    if sys.platform.startswith("win"):
        import subprocess
        p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
        p.communicate(input=text.encode("utf-8"))
        if p.returncode != 0:
            raise RuntimeError("Clipboard copy failed (clip).")
        return

    if sys.platform == "darwin":
        import subprocess
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(input=text.encode("utf-8"))
        if p.returncode != 0:
            raise RuntimeError("Clipboard copy failed (pbcopy).")
        return

    import subprocess
    for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        try:
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            p.communicate(input=text.encode("utf-8"))
            if p.returncode == 0:
                return
        except FileNotFoundError:
            continue

    raise RuntimeError("No clipboard tool found. Install xclip or xsel.")


def wait_for_keypress(prompt: str) -> str:
    """
    Wait for a key press before continuing.
    On Windows: any key via msvcrt.getch()
    On others: Enter via input()
    """
    print(prompt, end="", flush=True)
    if sys.platform.startswith("win"):
        import msvcrt
        ch = msvcrt.getch()
        try:
            return ch.decode("utf-8", errors="ignore")
        finally:
            print()
    else:
        s = input()
        return s


def encode_control_frame(obj: dict) -> str:
    payload = MAGIC + json.dumps(obj, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(payload).decode("ascii")


def raw_bytes_per_b64_chunk(b64_chunk_chars: int) -> int:
    """
    Base64 length is 4 * ceil(n/3).
    To keep encoded length <= b64_chunk_chars, use n = (b64_chunk_chars//4)*3.
    With 1KB chars => (1024//4)*3 = 768 bytes minimum.
    """
    n = (b64_chunk_chars // 4) * 3
    return max(1, n)


def send_file_chunked(file_path: Path, base_dir: Path, b64_chunk_chars: int) -> None:
    st = file_path.stat()
    rel_name = str(file_path.relative_to(base_dir)).replace("\\", "/")

    start_frame = {
        "type": "start",
        "name": rel_name,
        "size": int(st.st_size),
        "mtime": int(st.st_mtime),
    }
    end_frame = {
        "type": "end",
        "name": rel_name,
    }

    # Send START frame
    start_b64 = encode_control_frame(start_frame)
    s = wait_for_keypress(f"Press key to copy START frame for '{rel_name}' [Enter/any key, 'q' to quit]: ")
    if s.strip().lower() == "q":
        print("Aborted by user.")
        return
    copy_to_clipboard(start_b64)
    print("  - START frame copied.")

    # Send DATA frames
    chunk_bytes = raw_bytes_per_b64_chunk(b64_chunk_chars)
    total = st.st_size
    sent = 0
    chunk_index = 0
    t0 = time.time()

    with file_path.open("rb") as f:
        while True:
            data = f.read(chunk_bytes)
            if not data:
                break

            chunk_index += 1
            sent += len(data)
            b64_text = base64.b64encode(data).decode("ascii")

            pct = (sent / total * 100.0) if total else 100.0
            elapsed = max(time.time() - t0, 1e-6)
            speed = sent / elapsed

            print(
                f"  - Prepared chunk {chunk_index}: "
                f"{human_bytes(len(data))} raw -> {human_bytes(len(b64_text))} b64, "
                f"progress {pct:.2f}% ({human_bytes(sent)}/{human_bytes(total)}), "
                f"speed {human_bytes(int(speed))}/s"
            )

            s = wait_for_keypress(
                f"Press key to copy DATA chunk {chunk_index} for '{rel_name}' [Enter/any key, 'q' to quit]: "
            )
            if s.strip().lower() == "q":
                print("Aborted by user.")
                return

            copy_to_clipboard(b64_text)
            print("  - Copied.")

    # Send END frame
    end_b64 = encode_control_frame(end_frame)
    s = wait_for_keypress(f"Press key to copy END frame for '{rel_name}' [Enter/any key, 'q' to quit]: ")
    if s.strip().lower() == "q":
        print("Aborted by user.")
        return
    copy_to_clipboard(end_b64)
    print("  - END frame copied.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy chunked Base64 of files in a directory to clipboard, with keypress per frame/chunk."
    )
    parser.add_argument("dir", help="Target directory path")
    parser.add_argument("--recursive", action="store_true", help="Include subdirectories")
    parser.add_argument("--extensions", nargs="*", default=None, help="Only include these extensions (e.g. .txt .bin)")
    parser.add_argument(
        "--b64-chunk-kb",
        type=int,
        default=1024,
        help="Base64 chunk size in KB (minimum: 1KB). Default: 1024KB",
    )
    args = parser.parse_args()

    if args.b64_chunk_kb < 1:
        print("Error: --b64-chunk-kb must be >= 1.")
        return 1

    base_dir = Path(args.dir).expanduser().resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        print(f"Error: directory not found: {base_dir}")
        return 1

    files = list_files_sorted(base_dir, args.recursive)
    if args.extensions:
        exts = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in args.extensions}
        files = [p for p in files if p.suffix.lower() in exts]

    if not files:
        print("No files found.")
        return 0

    b64_chunk_chars = args.b64_chunk_kb * 1024
    raw_chunk = raw_bytes_per_b64_chunk(b64_chunk_chars)

    print(f"Directory: {base_dir}")
    print(f"Files found: {len(files)}")
    print(f"Base64 chunk size: {args.b64_chunk_kb} KB ({b64_chunk_chars} chars)")
    print(f"Raw bytes per DATA chunk: {raw_chunk} bytes")
    print("-" * 70)

    for i, fp in enumerate(files, start=1):
        rel_name = str(fp.relative_to(base_dir)).replace("\\", "/")
        print(f"[{i}/{len(files)}] {rel_name}")
        print(f"  - Size: {human_bytes(fp.stat().st_size)}")
        try:
            send_file_chunked(fp, base_dir, b64_chunk_chars)
        except Exception as e:
            print(f"Error: {e}")
            return 2

        if i < len(files):
            s = wait_for_keypress("Press key for next file... [Enter/any key, 'q' to quit]: ")
            if s.strip().lower() == "q":
                print("Done (user quit).")
                return 0
        print("-" * 70)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
