# Partition map and image comparison

All sizes below are MiB unless noted. “China” is the `P6ProC` 4.2.3 package, “Global”
the `Palma2_Pro_C` 4.2 package.

| Partition | China | Global | Identical |
|---|---:|---:|---|
| `system` | 3013.5 | 3061.8 | no |
| `system_ext` | 509.9 | 665.3 | no |
| `product` | 577.9 | 701.0 | no |
| `vendor` | 624.1 | 649.4 | no |
| `odm` | 1.0 | 1.0 | no |
| `boot` | 96.0 | 96.0 | no |
| `dtbo` | 8.0 | 8.0 | no |
| `recovery` | 96.0 | 96.0 | no |
| `abl` | 0.2 | 0.2 | no |
| `vbmeta` | 8 KiB | 8 KiB | no |
| `vbmeta_system` | 4 KiB | 4 KiB | no |
| `modem` | 140.8 | 140.8 | **yes** |
| `xbl` | 3.2 | 3.2 | **yes** |
| `aop` | 0.2 | 0.2 | **yes** |

`modem`, `xbl` and `aop` are byte-identical (SHA-256). That is the strongest single
signal that the RF/boot firmware is shared and does not need to change.

## Storage layout

UFS logical block size is **4096 bytes**. The GPT exposes:

| LUN | Contents |
|---|---|
| 0 | `persist`, `misc`, `frp`, `metadata`, `super` (6 GiB), `userdata`, `devinfo`? |
| 4 | bootloader/firmware partitions (`abl`, `xbl`, `tz`, `hyp`, `aop`, `boot`, `recovery`, `dtbo`, `vbmeta*`, `devinfo`) |
| 5 | `modemst1`, `modemst2`, `fsg`, `fsc` |

On the tested unit `devinfo` is on **LUN 4**, not LUN 0:

```
devinfo   off=0x579FE000  len=0x1000  sector(4K)=358910
```

Useful absolute sectors (4 KiB units):

| Partition | LUN | Sector |
|---|---:|---:|
| `abl_a` | 4 | 60686 |
| `abl_b` | 4 | 242186 |
| `boot_a` | 4 | 77454 |
| `boot_b` | 4 | 258954 |
| `recovery_a` | 4 | 102082 |
| `dtbo_a` | 4 | 126690 |
| `vbmeta_a` | 4 | 126674 |
| `vbmeta_system_a` | 4 | 126658 |
| `devinfo` | 4 | 358910 |
| `super` | 0 | 45576 (= `0x0B208000 / 4096`) |

## Logical partitions (`super`)

Dynamic partitions are inside `super`. On the China 4.2.3 unit the active A-slot metadata
held five real partitions plus three leftovers from the last OTA:

```
odm_a, product_a, system_a, system_ext_a, vendor_a
odm_a-cow, product_a-cow, system_a-cow
```

The COW entries occupied ~1.49 GiB at the tail, leaving **zero free space**. That is why
the global images cannot be written without resizing; see
[04-super-resize.md](04-super-resize.md).

After deleting the COW entries and resizing to the global image sizes:

```
system_a      3,210,575,872 B
system_ext_a    697,577,472 B
product_a       735,051,776 B
vendor_a        680,988,672 B
odm_a             1,060,864 B
total         5,078.6 MiB   < super 6,144 MiB
```

There is ~1.06 GiB left for future OTA snapshots.

## The A/B caveat

The China unit's LP metadata points `system_a` and `system_b` at the **same extents**;
only boot/abl/vbmeta are truly duplicated. The conversion writes the A slot. Slot B still
describes the old sizes and is not a valid fallback; if the bootloader ever falls back to
B, expect a failure. Recovery is EDL.
