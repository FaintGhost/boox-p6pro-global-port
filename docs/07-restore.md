# Restoring

Two different targets are useful.

## A. Back to a fresh global install (no root, no mods)

This is what “just flashed and first booted” looks like:

```sh
adb reboot edl

# stock global boot (removes Magisk)
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w boot_a fw_global/boot.img

# optional, only if they were changed
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w dtbo_a          fw_global/dtbo.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w vbmeta_a        fw_global/vbmeta.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w vbmeta_system_a fw_global/vbmeta_system.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w recovery_a      fw_global/recovery.img

# clear data, keep nothing from the modding session
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=0 e userdata
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=0 e metadata
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=0 e misc

python edl/edl.py reset --loader=palma2pro.bin --resetmode=reset
```

This removes `/data/adb` modules, installed apps, settings, launcher DB and MMKV edits.
The logical partitions stay global; the partition sizes stay resized (larger, harmless).

## B. Back to the China firmware

The China images are smaller than the resized partitions, so they fit without shrinking
the LP metadata. Flash the physical A-slot images and the five logical images with the
same extent tool, then wipe:

```sh
adb reboot edl
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w boot_a    fw/boot.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w dtbo_a    fw/dtbo.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w vbmeta_a  fw/vbmeta.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w vbmeta_system_a fw/vbmeta_system.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w recovery_a fw/recovery.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w abl_a      fw/abl.img
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=4 w abl_b      fw/abl.img

for p in odm system_ext product vendor system; do
  python scripts/flash_logical.py "fw/$p.img" lpdump_new.txt "${p}_a" \
    --loader palma2pro.bin --go
done

python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=0 e userdata
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=0 e metadata
python edl/edl.py --loader=palma2pro.bin --memory=ufs --lun=0 e misc
python edl/edl.py reset --loader=palma2pro.bin --resetmode=reset
```

The LP metadata still describes the larger global sizes. The China filesystems are
smaller than their partitions, which is normally fine, but the original layout is only
fully restored by replaying the original `super` metadata; that path was not tested.

## Re-locking

Writing the original `devinfo.img` back clears `is_unlocked`/`is_unlock_critical` and
re-enables AVB enforcement. On a unit that previously ran China 4.2.3, the global 4.2
`vbmeta` may be older than the stored rollback index and be rejected. Because the ABL
strips the lock commands, this is an EDL-only, unsupported operation.

If it fails to boot, write the unlocked `devinfo` again; EDL remains available. Keep both
images:

```
backup/devinfo.img            # locked, original
devinfo_unlocked.img          # two bytes set
```

## Keep off-machine

`persist`, `modemst1`, `modemst2`, `fsg`, `fsc`, `frp` and the full `super` dump are the
only way back to a fully original unit. They contain IMEI/calibration and must never be
committed to a repository.
