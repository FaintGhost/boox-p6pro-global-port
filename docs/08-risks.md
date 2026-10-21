# Risks, unknowns and things that are not “fixed”

This conversion was performed on **one** China unit. Treat it as a field report, not a
product.

## 1. Bootloader unlock is permanent in practice

- `verifiedbootstate=orange` on every boot.
- Play Integrity fails; banking, DRM and some games refuse to run.
- Widevine provisioning failed on the tested unit
  (`RkpdWidevine: Will not provision widevine certificates`).
- Play Protect certification registration is a separate, slow server-side process; it
  does not restore Play Integrity.
- Re-locking is unsupported (ABL lock commands stripped) and risky: AVB/rollback index
  may reject the global `vbmeta`. Recovery is possible through EDL, but there is no
  benefit.

## 2. Play certification

The device is a China SKU. Even with the GSF ID registered, Google may keep treating it
as uncertified. Most apps still install; certified-only apps may not.

## 3. OTA installation is unverified

The device reports the global fingerprint, so the OTA **API** answers. Whether a 4.3
package will **install** on the converted unit is untested. Risks:

- The China ABL's rollback index.
- The global `vbmeta` chain vs. the China ABL.
- Slot B is still described by the old LP metadata; a fallback boot would fail.
- A future OTA may also restore the partition sizes it expects.

If an OTA fails, EDL is the recovery.

## 4. Slot B is not a valid fallback

The China LP metadata points `system_a` and `system_b` at the same extents. The
conversion writes the A slot and resizes only A. Slot B still advertises the old sizes.
The bootloader's fallback logic is therefore not a safety net here.

## 5. Firmware-level apps

- `ProductionTest-release.apk` and the launcher's “Hello World” shortcut are in **both**
  China and global images. The shortcut is recreated by the launcher; deleting the DB row
  does not stick.
- The Onyx app market is included but is a China-oriented service; outside China it
  commonly reports a network/server error. Google Play is the global path.
- Removing either permanently means modifying the system image (custom firmware, breaks
  the Onyx signature, OTA overwrites it) or hiding it with root + a Magisk overlay.

## 6. Hardware functions not fully validated

- SIM data/calls (the `modem` image is identical, so the radio firmware is shared, but the
  global vendor RIL configuration and APN behaviour were not exhaustively tested).
- Camera, stylus, GPS, fingerprint, sensors, Bluetooth audio.
- One unit reported non-working volume keys after a series of launcher/config mods; after
  a clean wipe this was not re-confirmed. Treat volume-key behaviour as device-specific
  until tested on a clean install.

## 7. Data and warranty

- Every unlock or lock change wipes `/data`.
- The procedure voids the warranty.
- No proprietary binaries are distributed; you must obtain your own firmware.

## 8. Legal / licensing

Onyx's firmware and Google apps are not redistributable. The kernel source is not
published by Onyx (a GPL-2.0 issue that is theirs, not this repository's). The scripts and
notes here are MIT licensed.
