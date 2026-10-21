#!/usr/bin/env python3
"""Parallel HTTP range downloader for slow, single-connection CDNs.

Example:
  python pdl.py URL update.upx 2239926113 --threads 16 --md5 2e6266ee...
"""
import argparse
import hashlib
import os
import threading
import time
import urllib.request


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("output")
    ap.add_argument("size", type=int)
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--md5", default=None)
    ap.add_argument("--retries", type=int, default=0, help="0 = unlimited per-range retries")
    args = ap.parse_args()

    size = args.size
    threads = max(1, args.threads)
    done = 0
    lock = threading.Lock()
    start = time.time()
    stop = threading.Event()

    with open(args.output, "wb") as f:
        f.truncate(size)

    def worker(idx: int):
        nonlocal done
        chunk = (size + threads - 1) // threads
        begin = idx * chunk
        end = min(begin + chunk, size) - 1
        pos = begin
        attempts = 0
        fh = open(args.output, "r+b")
        try:
            while pos <= end and not stop.is_set():
                try:
                    req = urllib.request.Request(
                        args.url, headers={"Range": f"bytes={pos}-{end}"}
                    )
                    with urllib.request.urlopen(req, timeout=60) as r:
                        while pos <= end and not stop.is_set():
                            buf = r.read(65536)
                            if not buf:
                                raise IOError("short read")
                            fh.seek(pos)
                            fh.write(buf)
                            pos += len(buf)
                            with lock:
                                done += len(buf)
                except Exception as e:
                    attempts += 1
                    if args.retries and attempts > args.retries:
                        print(f"thread {idx}: giving up after {attempts} attempts: {e}")
                        stop.set()
                        return
                    time.sleep(2)
        finally:
            fh.close()

    def progress():
        while not stop.is_set():
            time.sleep(10)
            with lock:
                n = done
            elapsed = time.time() - start
            speed = n / elapsed if elapsed else 0
            pct = 100.0 * n / size
            eta = (size - n) / speed if speed else 0
            print(
                f"{pct:5.1f}%  {n / 1048576:8.1f} MiB  "
                f"{speed / 1048576:5.2f} MiB/s  ETA {eta / 60:5.1f} min",
                flush=True,
            )

    threading.Thread(target=progress, daemon=True).start()
    ts = [threading.Thread(target=worker, args=(i,)) for i in range(threads)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    if stop.is_set():
        print("aborted", flush=True)
        return 1
    got = os.path.getsize(args.output)
    print(f"done: {got} bytes", flush=True)
    if args.md5:
        h = hashlib.md5()
        with open(args.output, "rb") as f:
            for b in iter(lambda: f.read(8 << 20), b""):
                h.update(b)
        print(f"md5: {h.hexdigest()} (expected {args.md5})", flush=True)
        if h.hexdigest().lower() != args.md5.lower():
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
