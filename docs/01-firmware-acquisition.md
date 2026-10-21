# Getting the official firmware

Onyx does not publish per-model downloads anymore. The OTA service still does, but it
only answers for an **exact device fingerprint**. This is the part that makes the
conversion possible without a donor device.

## Endpoint

```
http://data.onyx-international.cn/api/firmware/update?where=<url-encoded JSON>
```

The China-facing host (`http://cn-data.onyx-international.cn`) speaks the same API.
Both return a single JSON document:

| Field | Meaning |
|---|---|
| `model` | model string (`P6ProC`, `Palma2_Pro_C`) |
| `fingerprint` | exact build fingerprint the package belongs to |
| `buildDisplayId` | e.g. `2026-08-10_11-54_4.2-rel_0810_74616a570` |
| `buildNumber` | e.g. `3316` |
| `md5` | package MD5; also the CDN path |
| `size` | bytes |
| `downloadUrlList` | `http://firmware.boox.com/<md5>/update.upx` |
| `wipeData` / `lockBootloader` | flags returned for the update |

Request body (`where`) is a JSON object:

```json
{
  "buildNumber": 0,
  "buildType": "user",
  "deviceMAC": "",
  "lang": "en_US",
  "model": "Palma2_Pro_C",
  "submodel": "",
  "fingerprint": "Onyx/Palma2_Pro_C/Palma2_Pro_C:11/.../3316:user/release-keys"
}
```

`lang=zh_CN` selects the China server/package; `en_US` the global one.

## Fingerprint format

Onyx uses the **vendor** build fingerprint (`ro.vendor.build.fingerprint`, also exposed
as `ro.vendor.build.onyxfp`):

```
Onyx/<model>/<model>:<vendor_api>/<build_display>/<build_number>:user/release-keys
```

The trap: **`<vendor_api>` is 11**, because the vendor is frozen at Android 11 on both
models. Using the system version (`:15` or `:13`) returns `204 No Content` for every
guess. With `:11` and the right build display/number, the server answers.

## Real examples

China, current build on the test unit:

```
Onyx/P6ProC/P6ProC:11/2026-09-29_16-47_4.2.3-rel_0929_71d37ca46/9022:user/release-keys
```

→ `P6ProC` 4.2.3, `2,047,921,056` bytes, md5 `cba6c38bca0a1921d6bcbed1d093c89d`.

Global, bootstrap fingerprint (from the public e/OS port recon of a retail Palma 2 Pro):

```
Onyx/Palma2_Pro_C/Palma2_Pro_C:11/2026-05-11_20-31_4.2-rel_05112/05112:user/release-keys
```

→ the server returns the **latest** global package for that model:

```
buildDisplayId = 2026-08-10_11-54_4.2-rel_0810_74616a570
buildNumber    = 3316
size           = 2,239,926,113
md5            = 2e6266ee60b0d4d317c12d47ffb2d74c
url            = http://firmware.boox.com/2e6266ee60b0d4d317c12d47ffb2d74c/update.upx
```

`buildNumber=3316` (current) returns `204`: already up to date.

## Why brute force is not an option

The fingerprint contains a build display with a 9-hex-digit build hash and a separate
build number. The miss space is at least `16^9 ≈ 6.9e10`; with a plausible 4–5 digit
build number it is much larger. The server returns only `200` or `204`, with no prefix
matching and no side channel. A valid fingerprint must come from a real device or from
public build metadata.

## Download, verify, decrypt

```sh
curl -L -o update_global.upx \
  http://firmware.boox.com/2e6266ee60b0d4d317c12d47ffb2d74c/update.upx

python - <<'PY'
import hashlib
h = hashlib.md5()
for b in iter(lambda: open('update_global.upx','rb').read(8<<20), b''):
    h.update(b)
print(h.hexdigest())
PY
```

Decrypt with [decryptBooxUpdateUpx](https://github.com/Hagb/decryptBooxUpdateUpx)
(`BooxKeys.csv` contains both `P6ProC` and `Palma2Pro`):

```sh
python DeBooxUpx.py P6ProC      update.upx        update.zip
python DeBooxUpx.py Palma2Pro   update_global.upx update_global.zip
```

The key name is `Palma2Pro` even though the OTA model string is `Palma2_Pro_C`.

Extract the A/B payload:

```sh
python extract_android_ota_payload.py update.zip fw/
python extract_android_ota_payload.py update_global.zip fw_global/
```

The payload contains 14 partitions: `abl`, `aop`, `boot`, `dtbo`, `modem`, `odm`,
`product`, `recovery`, `system`, `system_ext`, `vbmeta`, `vbmeta_system`, `vendor`,
`xbl`.

## OTA metadata

`META-INF/com/android/metadata` inside the decrypted zip is worth reading:

| | China 4.2.3 | Global 4.2 |
|---|---|---|
| `pre-device` | `P6ProC` | `Palma2_Pro_C` |
| `post-sdk-level` | 33 | 35 |
| `post-build` | `ONYX/TabBoox/TabBoox:13/...` | same (spoofed) |
| `post-build-incremental` | 640 | 230 |

The `pre-device` assertion is why the stock updater refuses the cross-region package.
EDL writes bypass it.

## Do not redistribute

The `.upx`/`.zip`/`.img` files contain Onyx proprietary code and Google apps. Keep them
local; this repository only documents how to fetch your own copy.
