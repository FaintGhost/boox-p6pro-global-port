# Making room in `super`

The global logical images are larger than the China ones:

| Partition | China | Global | Delta |
|---|---:|---:|---:|
| `system_a` | 3,159,908,352 | 3,210,575,872 | +50.7 MB |
| `system_ext_a` | 534,708,224 | 697,577,472 | +162.9 MB |
| `product_a` | 606,220,288 | 735,051,776 | +128.8 MB |
| `vendor_a` | 654,372,352 | 680,988,672 | +26.6 MB |
| `odm_a` | 1,056,768 | 1,060,864 | +4 KB |

The China `super` was fully allocated because the last OTA left three COW snapshots:

```
odm_a-cow       0.75 MB
product_a-cow   506 MB
system_a-cow    978 MB
```

They are inert leftovers. Deleting them frees ~1.49 GiB, enough for the resize.

## Use fastbootd, not the bootloader

`fastboot` in bootloader mode does not enumerate on this device. **fastbootd** (the
userspace fastboot implementation) does:

```sh
adb reboot fastboot
fastboot devices
fastboot getvar current-slot      # a
```

On Windows the device appears as `VID_18D1&PID_4EE0`; it needs the WinUSB driver
(Zadig → select the fastboot interface → WinUSB). Without it, `fastboot devices` is
empty.

## Delete the COW partitions

```sh
fastboot delete-logical-partition odm_a-cow
fastboot delete-logical-partition product_a-cow
fastboot delete-logical-partition system_a-cow
```

## Resize to the global image sizes

```sh
fastboot resize-logical-partition system_a     3210575872
fastboot resize-logical-partition system_ext_a  697577472
fastboot resize-logical-partition product_a     735051776
fastboot resize-logical-partition vendor_a      680988672
fastboot resize-logical-partition odm_a           1060864
```

Verify:

```sh
for p in system_a system_ext_a product_a vendor_a odm_a; do
  fastboot getvar partition-size:$p
done
```

Expected: `0xBF5D8000`, `0x29943000`, `0x2BD00000`, `0x28971000`, `0x103000`.

## Checkpoint

Reboot to Android **before flashing anything**:

```sh
fastboot reboot
```

The China 4.2.3 system should still boot. If it does not, stop; the LP metadata edit is
the only thing that changed.

## Offline alternative

If fastbootd is unavailable, the e/OS port's
[`lp-resize-partition.py`](https://github.com/spavikevik/palma2pro-eos/blob/main/scripts/lp-resize-partition.py)
can edit the LP metadata offline (append a linear extent from unallocated tail space,
rebuild the extents table, fix both metadata copies). It requires free tail space; on a
fully allocated China super that means deleting the COW partition records first, which
the tool does not do itself.
