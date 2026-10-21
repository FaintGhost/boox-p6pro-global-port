#!/usr/bin/env python3
"""Query Onyx's OTA API for a model and an exact build fingerprint.

Example:
  python ota_query.py --model Palma2_Pro_C --lang en_US --fingerprint \\
    "Onyx/Palma2_Pro_C/Palma2_Pro_C:11/2026-05-11_20-31_4.2-rel_05112/05112:user/release-keys"
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

HOSTS = {
    "global": "http://data.onyx-international.cn",
    "china": "http://cn-data.onyx-international.cn",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--fingerprint", required=True)
    ap.add_argument("--lang", default="en_US")
    ap.add_argument("--host", choices=sorted(HOSTS), default="global")
    ap.add_argument("--build-number", type=int, default=0)
    args = ap.parse_args()

    where = {
        "buildNumber": args.build_number,
        "buildType": "user",
        "deviceMAC": "",
        "lang": args.lang,
        "model": args.model,
        "submodel": "",
        "fingerprint": args.fingerprint,
    }
    url = HOSTS[args.host] + "/api/firmware/update?where=" + urllib.parse.quote(
        json.dumps(where, separators=(",", ":"))
    )

    try:
        resp = urllib.request.urlopen(url, timeout=30)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.reason}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"request failed: {e}", file=sys.stderr)
        return 1

    body = resp.read()
    if not body:
        print("204 No Content: no update for this fingerprint", file=sys.stderr)
        return 2

    d = json.loads(body)
    for key in (
        "model",
        "fingerprint",
        "buildDisplayId",
        "buildNumber",
        "md5",
        "size",
        "downloadUrlList",
        "wipeData",
        "lockBootloader",
        "fwType",
    ):
        print(f"{key}: {d.get(key)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
