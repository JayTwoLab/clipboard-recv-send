#!/usr/bin/env python3
import argparse
import base64
import math
import subprocess
import time
from pathlib import Path
from zlib import crc32

MAGIC = "B64CLIP1"

def parse_size(s: str) -> int:
    s = s.strip().lower()
    mul = 1
    if s.endswith(("kb", "k")):
        mul = 1024
        s = s[:-2] if s.endswith("kb") else s[:-1]
    elif s.endswith(("mb", "m")):
        mul = 1024 * 1024
        s = s[:-2] if s.endswith("mb") else s[:-1]
    elif s.endswith(("gb", "g")):
        mul = 1024 * 1024 * 1024
        s = s[:-2] if s.endswith("gb") else s[:-1]
    n = int(float(s) * mul)
    if n <= 0:
        raise ValueError("size must be > 0")
    return n

def human(n: float) -> str:
    n = float(n)
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:.2f}{u}"
        n /= 1024.0
    return f"{n:.2f}PB"

def set_clipboard_win(text: str) -> None:
    # Windows: write to clipboard via clip.exe (UTF-8)
    subprocess.run(["cmd.exe", "/c", "clip"], input=text.encode("utf-8"), check=True)

def make_header(seq: int, total: int, payload_len: int, crc_hex: str, file_size: int, file_name: str) -> str:
    safe_name = file_name.replace("|", "_")
    return (f"{MAGIC}|seq={seq}|total={total}|len={payload_len}|crc={crc_hex}"
            f"|fsize={file_size}|name={safe_name}")

def b64_payload_chunks(path: Path, payload_chunk_bytes: int, read_block: int = 1024 * 1024):
    buf = bytearray()
    rem = b""
    in_done = 0
    in_total = path.stat().st_size

    with path.open("rb") as f:
        while True:
            b = f.read(read_block)
            if not b:
                break
            in_done += len(b)
            b = rem + b
            cut = (len(b) // 3) * 3
            main, rem = b[:cut], b[cut:]
            if main:
                buf += base64.b64encode(main)

            while len(buf) >= payload_chunk_bytes:
                payload = bytes(buf[:payload_chunk_bytes]).decode("ascii")
                del buf[:payload_chunk_bytes]
                yield payload, in_done, in_total

        if rem:
            buf += base64.b64encode(rem)
        if buf:
            yield bytes(buf).decode("ascii"), in_done, in_total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", help="input directory path")
    ap.add_argument("--chunk", default="4m", help="base64 payload chunk size (default 4m)")
    ap.add_argument("--no-wait-first", action="store_true", help="wait before first copy")
    args = ap.parse_args()

    dir_path = Path(args.dir)
    if not dir_path.exists() or not dir_path.is_dir():
        raise SystemExit(f"directory not found: {dir_path}")

    payload_chunk_bytes = parse_size(args.chunk)
    files = sorted([p for p in dir_path.iterdir() if p.is_file()])
    if not files:
        raise SystemExit(f"no files found in directory: {dir_path}")

    print(f"Mode: clipboard sender (Windows) ({MAGIC})")
    print(f"Directory: {dir_path}")
    print(f"File count: {len(files)}")
    print(f"Payload chunk (base64): {human(payload_chunk_bytes)}")
    print(f"Interval: fixed 10s (00,10,20,...)")
    print("-" * 80)

    interval_sec = 10.0
    for file_path in files:
        file_size = file_path.stat().st_size
        est_b64_size = int(math.ceil(file_size / 3) * 4)
        est_total_chunks = max(1, int(math.ceil(est_b64_size / payload_chunk_bytes)))
        total_for_header = est_total_chunks

        print(f"Sending file: {file_path.name} ({human(file_size)})")
        seq = 0
        t0 = time.time()
        for payload, in_done, in_total in b64_payload_chunks(file_path, payload_chunk_bytes):
            now = time.time()
            if seq == 0 and not args.no_wait_first:
                wait = interval_sec - (now % interval_sec)
                if wait < 0.01:
                    wait += interval_sec
                time.sleep(wait)
            elif seq > 0:
                now = time.time()
                wait = interval_sec - (now % interval_sec)
                if wait < 0.01:
                    wait += interval_sec
                time.sleep(wait)

            seq += 1
            c = crc32(payload.encode("ascii")) & 0xFFFFFFFF
            crc_hex = f"{c:08X}"

            header = make_header(seq, total_for_header, len(payload), crc_hex, file_size, file_path.name)
            text = header + "\n" + payload

            try:
                set_clipboard_win(text)
            except Exception as e:
                raise SystemExit(f"ERROR: clipboard write failed: {e}")

            elapsed = time.time() - t0
            speed = in_done / elapsed if elapsed > 0 else 0
            pct = (in_done / in_total * 100.0) if in_total else 100.0
            eta = (in_total - in_done) / speed if speed > 0 else 0

            print(
                f"[{seq}/{total_for_header}] "
                f"clipboard_total={human(len(text))} payload={human(len(payload))} | "
                f"file_processed={human(in_done)}/{human(in_total)} ({pct:6.2f}%) | "
                f"speed={human(speed)}/s | eta={eta:6.1f}s | crc32={crc_hex}"
            )

        print("-" * 80)
    print("Done")

if __name__ == "__main__":
    main()
