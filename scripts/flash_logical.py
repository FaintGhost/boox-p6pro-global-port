#!/usr/bin/env python3
"""Write a logical-partition image into its super extents over EDL.

The image is split into the extents reported by `lpdump` (or by
palma2pro-eos/scripts/lpdump-from-super.py) and written in 32 MiB chunks with
`edl ws`. This keeps every USB transfer short; long streams are unreliable on
this hardware.

Example:
  python flash_logical.py fw_global/system.img lpdump.txt system_a \\
      --loader palma2pro.bin --edl ../p6pro/edl/edl.py --go

Without --go it prints the plan only.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile


def read_extents(path: str, part: str):
    out = []
    inside = False
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if re.search(rf"Name:\s+{re.escape(part)}\s*$", line):
                inside = True
                continue
            if inside:
                if line.strip().startswith("---"):
                    break
                m = re.match(r"\s*(\d+)\s*\.\.\s*(\d+)\s+linear\s+super\s+(\d+)", line)
                if m:
                    start, end, phys = (int(x) for x in m.groups())
                    out.append((phys, end - start + 1))
    return out


def write_sector(args, sector: int, path: str) -> bool:
    cmd = [
        sys.executable,
        args.edl,
        f"--loader={args.loader}",
        "--memory=ufs",
        f"--lun={args.lun}",
        "ws",
        str(sector),
        path,
    ]
    for attempt in range(args.retries):
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if "Wrote" in r.stdout:
            return True
        tail = (r.stdout.strip().splitlines() or [""])[-1]
        print(f"    retry {attempt + 1}: {tail}", flush=True)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("lpdump")
    ap.add_argument("partition")
    ap.add_argument("--edl", default="edl/edl.py", help="path to bkerler/edl edl.py")
    ap.add_argument("--loader", default="palma2pro.bin")
    ap.add_argument("--lun", type=int, default=0)
    ap.add_argument("--super-offset", type=lambda x: int(x, 0), default=0x0B208000)
    ap.add_argument("--sector-size", type=int, default=4096)
    ap.add_argument("--chunk-mib", type=int, default=32)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--go", action="store_true")
    args = ap.parse_args()

    ext = read_extents(args.lpdump, args.partition)
    if not ext:
        print(f"no extents for {args.partition}", file=sys.stderr)
        return 1

    total = sum(n for _, n in ext) * 512
    size = os.path.getsize(args.image)
    print(f"{args.partition}: {len(ext)} extents, {total} bytes; image {size} bytes")
    if size > total:
        print("image larger than partition -- refusing", file=sys.stderr)
        return 1

    chunk = args.chunk_mib * 1024 * 1024
    tmpdir = tempfile.mkdtemp(prefix="extflash-")
    tmp = os.path.join(tmpdir, "chunk.bin")
    img_off = 0

    for i, (phys512, n512) in enumerate(ext, 1):
        byte_off = args.super_offset + phys512 * 512
        nbytes = n512 * 512
        if byte_off % args.sector_size or nbytes % args.sector_size:
            print(f"extent {i} not sector-aligned -- refusing", file=sys.stderr)
            return 1
        sector = byte_off // args.sector_size
        ext_done = 0
        while ext_done < nbytes and img_off < size:
            take = min(chunk, nbytes - ext_done, size - img_off)
            with open(args.image, "rb") as src, open(tmp, "wb") as dst:
                src.seek(img_off)
                left = take
                while left:
                    buf = src.read(min(8 << 20, left))
                    if not buf:
                        break
                    dst.write(buf)
                    left -= len(buf)
            pad = (-os.path.getsize(tmp)) % args.sector_size
            if pad:
                with open(tmp, "ab") as dst:
                    dst.write(b"\0" * pad)
            if args.go:
                if not write_sector(args, sector, tmp):
                    print(f"FAILED {args.partition} at sector {sector}", file=sys.stderr)
                    return 1
                print(
                    f"  {args.partition} ext{i} {img_off // 1048576}/{size // 1048576} MiB "
                    f"-> sector {sector} ({take // 1048576} MiB)",
                    flush=True,
                )
            else:
                print(f"  [plan] ext{i} sector={sector} take={take}")
            img_off += take
            sector += (take + args.sector_size - 1) // args.sector_size
            ext_done += take
        if img_off >= size:
            break

    print(f"{args.partition} done: {img_off}/{size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
