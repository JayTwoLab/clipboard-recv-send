#!/usr/bin/env python3
import argparse
import base64
import binascii
import subprocess
import time
from pathlib import Path
from zlib import crc32

MAGIC = "B64CLIP1"

def human(n: float) -> str:
    n = float(n)
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:.2f}{u}"
        n /= 1024.0
    return f"{n:.2f}PB"

def get_clipboard_win() -> str:
    # PowerShell: read clipboard text
    # -Raw keeps newlines; redirect errors to empty
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        "try { Get-Clipboard -Raw } catch { '' }"
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout or ""

def parse_header_line(line: str) -> dict:
    parts = line.strip().split("|")
    if not parts or parts[0] != MAGIC:
        raise ValueError("bad magic")
    kv = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            kv[k.strip()] = v.strip()
    for req in ("seq", "total", "len", "crc"):
        if req not in kv:
            raise ValueError(f"missing field: {req}")
    kv["seq"] = int(kv["seq"])
    kv["total"] = int(kv["total"])
    kv["len"] = int(kv["len"])
    kv["crc"] = kv["crc"].upper()
    if "fsize" in kv:
        kv["fsize"] = int(kv["fsize"])
    return kv

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output", help="output file path")
    ap.add_argument("--interval", type=float, default=2.0, help="polling interval seconds (default 2)")
    ap.add_argument("--timeout", type=float, default=0.0, help="stop after N seconds without progress (0=never)")
    ap.add_argument("--append", action="store_true", help="append to existing file")
    ap.add_argument("--expect-total", type=int, default=0, help="optional: override total chunks expectation")
    args = ap.parse_args()

    out_path = Path(args.output)
    mode = "ab" if args.append else "wb"

    interval = max(0.2, args.interval)
    timeout = max(0.0, args.timeout)

    expected_seq = 1
    total_chunks = args.expect_total if args.expect_total > 0 else None
    file_name = None
    file_size = None

    total_payload_b64 = 0
    total_out = 0
    buf = ""

    last_clip = None
    last_progress_t = time.time()
    t0 = time.time()

    print(f"Mode: clipboard receiver (polling, Windows) ({MAGIC})")
    print(f"Output: {out_path}")
    print(f"Interval: {interval:.1f}s")
    if timeout > 0:
        print(f"Timeout (no progress): {timeout:.1f}s")
    print("-" * 80)

    with out_path.open(mode) as out:
        while True:
            if timeout > 0 and (time.time() - last_progress_t) > timeout:
                print("Stopped: timeout without progress")
                break

            clip = get_clipboard_win()
            if not clip or clip == last_clip:
                time.sleep(interval)
                continue

            last_clip = clip

            if "\n" not in clip:
                time.sleep(interval)
                continue

            header_line, payload = clip.split("\n", 1)
            payload = payload.strip()
            if not payload:
                time.sleep(interval)
                continue

            try:
                h = parse_header_line(header_line)
            except Exception:
                time.sleep(interval)
                continue

            seq = h["seq"]
            if total_chunks is None:
                total_chunks = h["total"]
            if file_name is None and "name" in h:
                file_name = h["name"]
            if file_size is None and "fsize" in h:
                file_size = h["fsize"]

            if seq != expected_seq:
                # Missing or overwritten chunk
                print(f"Skipped: seq mismatch (got {seq}, expected {expected_seq})")
                time.sleep(interval)
                continue

            if h["len"] != len(payload):
                print(f"Skipped: length mismatch (header {h['len']}, actual {len(payload)})")
                time.sleep(interval)
                continue

            c = crc32(payload.encode("ascii")) & 0xFFFFFFFF
            crc_hex = f"{c:08X}"
            if crc_hex != h["crc"]:
                print(f"Skipped: crc mismatch (header {h['crc']}, actual {crc_hex})")
                time.sleep(interval)
                continue

            total_payload_b64 += len(payload)
            buf += payload

            dec_len = (len(buf) // 4) * 4
            if dec_len > 0:
                to_decode = buf[:dec_len]
                buf = buf[dec_len:]
                try:
                    data = base64.b64decode(to_decode, validate=True)
                except binascii.Error as e:
                    print(f"ERROR: base64 decode failed: {e}")
                    return 2
                out.write(data)
                total_out += len(data)

            expected_seq += 1
            last_progress_t = time.time()

            elapsed = time.time() - t0
            rate = total_out / elapsed if elapsed > 0 else 0
            prog = f"[{seq}/{total_chunks}] " if total_chunks else f"[{seq}] "

            meta = []
            if file_name:
                meta.append(f"name={file_name}")
            if file_size is not None:
                meta.append(f"fsize={human(file_size)}")
            meta_s = (" | " + " ".join(meta)) if meta else ""

            print(
                f"{prog}"
                f"received_payload_b64={human(total_payload_b64)} | "
                f"written={human(total_out)} | "
                f"write_rate={human(rate)}/s | "
                f"crc32={crc_hex}"
                f"{meta_s}"
            )

            if total_chunks and seq >= total_chunks:
                break

            time.sleep(interval)

    if buf.strip():
        try:
            data = base64.b64decode(buf, validate=True)
        except binascii.Error as e:
            print(f"ERROR: trailing base64 invalid: {e}")
            return 2
        with out_path.open("ab") as out:
            out.write(data)
        total_out += len(data)

    print("-" * 80)
    print(f"Done. Output={out_path} written={human(total_out)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
