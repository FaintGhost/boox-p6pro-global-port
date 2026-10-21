# Device identity: `P6ProC` vs `Palma2_Pro_C`

The Chinese **P6 Pro 小彩马** and the global **Palma 2 Pro** are the same hardware
platform sold under different model strings and firmware regions.

| Property | China (`P6ProC`) | Global (`Palma2_Pro_C`) |
|---|---|---|
| Marketing name | P6 Pro 小彩马 | Palma 2 Pro (OPC1410R) |
| SoC | Qualcomm SM7225 (Snapdragon 750G) | same |
| HWID | `0x0013f0e1` | `0x0013f0e1` |
| Display | 6.13" Kaleido 3, 824×1648 | same |
| RAM / storage | 8 GB / 128 GB | same |
| System | Android 13 | Android 15 |
| Vendor | Android 11, VNDK 30 | Android 11, VNDK 30 |
| Active slot | `_a` | `_b` (retail) |
| Partitions | 14 in the OTA payload, A/B, `super` 6 GiB | same 14 partitions |
| Bootloader | Onyx ABL, unlock commands stripped | Onyx ABL, same behaviour |

## Evidence used

- `ro.board.platform=lito`, `ro.product.first_api_level=30`, `ro.vndk.version=30` on both.
- The OTA payloads expose the same 14 partition names and the same partition order.
- `xbl`, `modem` and `aop` images are **byte-identical** between the China 4.2.3 package
  and the global 4.2 package (SHA-256).
- `boot`, `dtbo`, `abl`, `vendor`, `odm`, `system`, `system_ext`, `product` and the
  `vbmeta*` images differ.
- Both vendor fingerprints are Android 11:
  `Onyx/P6ProC/P6ProC:11/...` and `Onyx/Palma2_Pro_C/Palma2_Pro_C:11/...`.

## What this means

The conversion is a **system-side swap** on a shared SM7225 / Android 11 vendor
baseline. The vendor is not rebuilt; the global `system` is a newer qssi image over the
same frozen vendor generation. That is also how Onyx ships Android 15 on the retail
Palma 2 Pro.

It does **not** mean the two models are interchangeable in Onyx's eyes: the OTA
metadata asserts `pre-device`, the signing domain and the model string differ, and the
global package is encrypted with a different per-model key. The stock updater will
reject it. See [01-firmware-acquisition.md](01-firmware-acquisition.md).

## Known differences that remain

- China `abl` is kept (the global `abl` differs; `xbl` is identical).
- `devinfo` is patched to unlocked.
- `persist`, `modemst1/2`, `fsg`, `fsc`, `frp` remain the China unit's own data
  (IMEI, calibration, factory records).
- The global `system` contains Onyx's app market and a factory `ProductionTest` app;
  see [06-first-boot.md](06-first-boot.md).
