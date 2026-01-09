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
    ap.add_argument("dir", help="output directory path")
    ap.add_argument("--timeout", type=float, default=0.0, help="stop after N seconds without progress (0=never)")
    args = ap.parse_args()

    out_dir = Path(args.dir)
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    # interval 인자 무시, 실제 시간 기준 10초마다(5초 offset) polling
    interval_sec = 10.0
    offset_sec = 5.0
    timeout = max(0.0, args.timeout)

    # 여러 파일 수신을 위한 상태 변수
    expected_seq = 1
    total_chunks = None
    file_name = None
    file_size = None
    total_payload_b64 = 0
    total_out = 0
    buf = ""
    last_clip = None
    last_progress_t = time.time()
    t0 = time.time()

    print(f"Mode: clipboard receiver (polling, Windows) ({MAGIC})")
    print(f"Output directory: {out_dir}")
    print(f"Interval: fixed 10s (5s offset)")
    if timeout > 0:
        print(f"Timeout (no progress): {timeout:.1f}s")
    print("-" * 80)

    out = None
    while True:
        # 다음 10초 배수+5초까지 남은 시간 계산
        now = time.time()
        next_tick = ((now // interval_sec) * interval_sec) + offset_sec
        if now % interval_sec >= offset_sec:
            next_tick += interval_sec
        wait = next_tick - now
        if wait > 0.01:
            time.sleep(wait)

        if timeout > 0 and (time.time() - last_progress_t) > timeout:
            print("Stopped: timeout without progress")
            break

        clip = get_clipboard_win()
        if not clip or clip == last_clip:
            continue

        last_clip = clip

        if "\n" not in clip:
            continue

        header_line, payload = clip.split("\n", 1)
        payload = payload.strip()
        if not payload:
            continue

        try:
            h = parse_header_line(header_line)
        except Exception:
            continue

        seq = h["seq"]
        if total_chunks is None or (file_name is not None and h["name"] != file_name):
            # 새 파일 시작
            if out:
                if buf.strip():
                    try:
                        data = base64.b64decode(buf, validate=True)
                    except binascii.Error as e:
                        print(f"ERROR: trailing base64 invalid: {e}")
                        return 2
                    out.write(data)
                    total_out += len(data)
                out.close()
                print("-" * 80)
                print(f"Done. Output={out_path} written={human(total_out)}")
            file_name = h["name"]
            file_size = h["fsize"] if "fsize" in h else None
            total_chunks = h["total"]
            expected_seq = 1
            total_payload_b64 = 0
            total_out = 0
            buf = ""
            out_path = out_dir / file_name
            out = open(out_path, "wb")
            t0 = time.time()
            print(f"Receiving file: {file_name} ({human(file_size)})")

        if seq != expected_seq:
            print(f"Skipped: seq mismatch (got {seq}, expected {expected_seq})")
            continue

        if h["len"] != len(payload):
            print(f"Skipped: length mismatch (header {h['len']}, actual {len(payload)})")
            continue

        c = crc32(payload.encode("ascii")) & 0xFFFFFFFF
        crc_hex = f"{c:08X}"
        if crc_hex != h["crc"]:
            print(f"Skipped: crc mismatch (header {h['crc']}, actual {crc_hex})")
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
            # 파일 수신 완료
            if buf.strip():
                try:
                    data = base64.b64decode(buf, validate=True)
                except binascii.Error as e:
                    print(f"ERROR: trailing base64 invalid: {e}")
                    return 2
                out.write(data)
                total_out += len(data)
            out.close()
            print("-" * 80)
            print(f"Done. Output={out_path} written={human(total_out)}")
            file_name = None
            file_size = None
            total_chunks = None
            expected_seq = 1
            total_payload_b64 = 0
            total_out = 0
            buf = ""
            out = None
            continue

if __name__ == "__main__":
    raise SystemExit(main())
