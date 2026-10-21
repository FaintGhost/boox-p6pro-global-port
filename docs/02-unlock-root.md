# Unlock and optional root

This step is independent of the region swap but is required before flashing a modified
`boot`/`vbmeta`, and it is how the device was rooted for the final checks.

The procedure below is a summary of prior public work; follow the originals for the
fully tested sequence:

- [Kisuke-CZE/Palma_2_Pro-tips](https://github.com/Kisuke-CZE/Palma_2_Pro-tips)
- [dynamicfire/boox-p6pro-root](https://github.com/dynamicfire/boox-p6pro-root)
- [Renate's EDL notes](https://www.temblast.com/edl.htm)

## Facts that shape the procedure

- `fastboot` in bootloader mode is unusable on this device (USB is not initialized, the
  unlock commands are stripped).
- **fastbootd** (userspace, reached with `adb reboot fastboot`) *does* work and accepts
  `delete-logical-partition` / `resize-logical-partition`; it rejects `flash`.
- EDL (Qualcomm 9008) is always available and is the only write channel for partitions.

## 1. EDL and backups

```sh
adb reboot edl
python edl/edl.py --loader=palma2pro.bin --memory=ufs printgpt
```

Loader: the SM7225/UFS Firehose `palma2pro.bin` (same loader as the Palma 2 Pro).
`super` is on LUN 0, `boot`/`abl`/`vbmeta` on LUN 4, modem calibration on LUN 5.

Back up every partition except `userdata` (and keep the result off the machine):

```sh
python edl/edl.py --loader=palma2pro.bin --memory=ufs rl backup/ --skip=userdata
```

Large reads can stall (see [05-edl-flash.md](05-edl-flash.md)); the device-unique
partitions are small and must be captured individually:

```sh
for p in persist misc frp metadata devinfo dip apdp storsec uefivarstore secdata; do
  python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=0 r "$p" "backup/$p.img"
done
for p in modemst1 modemst2 fsg fsc; do
  python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=5 r "$p" "backup/$p.img"
done
```

`modemst1/2` and `fsg` carry IMEI/calibration. Losing them means no cellular.

## 2. `devinfo` unlock

The unlock state is two bytes in `devinfo` (standard Qualcomm layout):

| Offset | Field |
|---|---|
| `0x0D` | `is_unlocked` |
| `0x0E` | `is_unlock_critical` |

Set both to `0x01` and write the partition back:

```sh
python - <<'PY'
d = bytearray(open('backup/devinfo.img','rb').read())
d[0x0D] = d[0x0E] = 1
open('devinfo_unlocked.img','wb').write(d)
PY
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w devinfo devinfo_unlocked.img
```

On the tested unit the stock ABL also required the OEM-unlock toggle to be enabled
first. The published method temporarily flashes the Fairphone 4 ABL (same SM7225) to
expose it:

```sh
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w abl_a abl-fp4.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w abl_b abl-fp4.img
```

Then boot Android, open Developer options, enable **OEM unlocking**, and only then write
the patched `devinfo`. Finally restore the stock ABL:

```sh
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w abl_a fw/abl.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w abl_b fw/abl.img
```

The next boot lands in recovery (“Can't load Android system”); choose
**Factory data reset**. This wipe is unavoidable.

## 3. Root (optional)

With the global `boot.img`:

1. Install Magisk on the device.
2. `Install → Select and Patch a File → boot.img`.
3. Pull the patched image back to the host.
4. Flash it:

```sh
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w boot_a magisk_patched.img
```

Verify:

```sh
adb shell su -c id
# uid=0(root) gid=0(root) ... context=u:r:magisk:s0
```

## 4. What root is useful for here

- Reading `gservices.db` (GSF ID for Play certification).
- Hiding firmware apps with a Magisk overlay module.
- Editing Onyx launcher/config databases.
- It is **not** required for the region swap itself.

## 5. Re-locking

Not recommended. The stock ABL strips the lock commands, so re-locking means writing the
original `devinfo` back through EDL. That re-enables AVB/rollback enforcement; a global
4.2 `vbmeta` on a unit that previously ran China 4.2.3 may fail the rollback index.
Recovery is possible (write the unlocked `devinfo` again), but the benefit is close to
zero: the device is still a China SKU, Play certification does not become automatic, and
Widevine does not return.

See [08-risks.md](08-risks.md).
