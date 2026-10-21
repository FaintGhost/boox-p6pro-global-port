# EDL flashing

Everything that bypasses the OTA's `pre-device` assertion goes through Qualcomm EDL
(9008). The host tool used here is [bkerler/edl](https://github.com/bkerler/edl).

## Loader and transport

```sh
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 printgpt
```

- `palma2pro.bin` is the SM7225/UFS Firehose loader (same one the Palma 2 Pro uses).
- The device advertises 4096-byte sectors. `super` is LUN 0; `boot`/`abl`/`vbmeta` LUN 4.
- A successful command leaves the Firehose loader running; the next invocation reuses it
  (“Mode detected: firehose”). A **stalled read wedges the loader**: `reset` and further
  commands return `USBError(32, 'Pipe error')` until the device is power-cycled.

## The USB IN problem (important)

On the tested hardware the device→host bulk endpoint is unstable. Observed repeatedly:

- A 128 MB `rs` read dies at ~114 MB.
- A 6 GB `super` read dies at ~10–165 MB, then retries forever.
- `adb pull` of 96 MB dies at ~1.2 MB, while `adb push` of the same file runs at 64 MB/s.

Writes (host→device) are reliable: a 96 MB `boot` write and ~5.3 GB of logical writes
completed without corruption. Practical rules:

1. Do **not** stream large reads. Read only the first 1–4 MB of a partition (enough for
   GPT/LP metadata) or use small chunks.
2. For big files **from** the device, use **adb over Wi-Fi**
   (`adb tcpip 5555; adb connect <ip>:5555`) or LocalSend.
3. Write in chunks (32 MB) so a stall only loses one chunk.

## Physical partitions

Flash the global stock images to the A slot:

```sh
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w boot_a           fw_global/boot.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w dtbo_a           fw_global/dtbo.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w vbmeta_a         fw_global/vbmeta.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w vbmeta_system_a  fw_global/vbmeta_system.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w recovery_a       fw_global/recovery.img
```

Keep the China `abl`, `xbl` and `modem`. Restore the stock ABL if the FP4 one is still
installed:

```sh
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w abl_a fw/abl.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w abl_b fw/abl.img
```

## Logical partitions

A logical partition is a list of extents inside `super`. `lpdump` (or
`palma2pro-eos/scripts/lpdump-from-super.py`) gives `(offset_512, length_512)` per
extent, relative to `super`.

Convert to absolute 4 KiB sectors:

```
device_sector = (0x0B208000 + offset_512 * 512) / 4096
              = 45576 + offset_512 / 8
```

The helper `scripts/flash_logical.py` does the split and writes each 32 MB chunk with
`edl ws`:

```sh
python scripts/flash_logical.py fw_global/odm.img        lpdump_new.txt odm_a        --loader palma2pro.bin --go
python scripts/flash_logical.py fw_global/vendor.img     lpdump_new.txt vendor_a     --loader palma2pro.bin --go
python scripts/flash_logical.py fw_global/system_ext.img lpdump_new.txt system_ext_a --loader palma2pro.bin --go
python scripts/flash_logical.py fw_global/product.img    lpdump_new.txt product_a    --loader palma2pro.bin --go
python scripts/flash_logical.py fw_global/system.img     lpdump_new.txt system_a     --loader palma2pro.bin --go
```

The script refuses an image larger than the extents and pads the final chunk to 4 KiB.

## Wipe and reboot

```sh
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=0 e userdata
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=0 e metadata
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=0 e misc
python edl/edl.py reset --loader=palma2pro.bin --resetmode=reset
```

`reset` may itself hit the pipe error. If it does, hold the power button for ~20 s, then
press it once. The first boot is slow (new system, new data).

## Failure recovery

- Any failed write leaves EDL reachable; re-enter with `adb reboot edl` or the
  power+volume combo and retry the chunk.
- A boot failure after a partial write is recoverable by rewriting the stock images.
- The China images, `devinfo` and the loaders are the rollback set; see
  [07-restore.md](07-restore.md).
