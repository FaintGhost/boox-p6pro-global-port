# First boot and post-conversion notes

After the writes and the wipe, the device boots the global 4.2 system:

```
ro.product.device              = Palma2_Pro_C
ro.build.version.release       = 15
ro.build.display.id            = 2026-08-10_11-54_4.2-rel_0810_74616a570
ro.vendor.build.fingerprint    = Onyx/Palma2_Pro_C/Palma2_Pro_C:11/.../3316:user/release-keys
ro.boot.verifiedbootstate      = orange
```

Play Store (`com.android.vending`), GMS and GSF are present. Onyx's own apps are the
global set. The device is usable as a normal Android tablet; the sections below are
things that behave differently from a retail Palma 2 Pro.

## Play Protect certification

The device is a China SKU. If Play Store says “Device isn't certified”:

1. The registration page needs the **GSF Android ID**, not
   `Settings.Secure.ANDROID_ID` and not `adb shell settings get secure android_id`.
2. With root, read it from GMS:

```sh
adb shell su -c "cp /data/user/0/com.google.android.gms/databases/gservices.db /sdcard/Download/"
adb pull /sdcard/Download/gservices.db
python - <<'PY'
import sqlite3
print(sqlite3.connect('gservices.db').execute(
    "select name,value from main where name='android_id'").fetchall())
PY
```

The value is a 64-bit ID; the page accepts **16 hex** or **19 decimal**. The decimal form
must be 19 digits; a 20-digit decimal is the *Settings* ID and is rejected.

3. Submit it at `https://www.google.com/android/uncertified/`, wait, force-stop Play
   Store, reopen.

The status is cached in GSF (`uncertified_status`, ~24 h expiry). Registration can be
slow. It does **not** fix Play Integrity: the unlocked bootloader is a separate verdict.

## Pixel-style assistant on the power button

AOSP uses `Settings.Global.POWER_BUTTON_LONG_PRESS = 5` for “long press power for
assistant”, with `POWER_BUTTON_VOLUME_UP` moved to the power menu:

```sh
adb shell settings put global power_button_long_press 5
adb shell settings put global key_chord_power_volume_up 2
```

On the tested unit, long-pressing power opens
`com.google.android.googlequicksearchbox/...assistant.surfaces.voice.robin.ui.floaty.activity.FloatyActivity`
— the Gemini floaty, not the power menu. Power + Volume Up still opens the power menu.
The setting survives reboots but **not** a factory reset.

## Gemini and the Google app

The Gemini app (`com.google.android.apps.bard`) delegates to the Google app's assistant
surface. If it says “enable Google app” while the Google app is installed, the usual cause
is that the Google app is a **user app** (`/data/app`, no `SYSTEM` flag). Gemini expects a
system install.

One working fix (used here) is a Magisk module that mounts the installed Google app plus
the Google feature/permission XMLs as `/system/priv-app/Velvet`. After a reboot the
package shows `pkgFlags=[ SYSTEM ... UPDATED_SYSTEM_APP ... ]` and Gemini opens the
assistant surface. This is optional and independent of the region swap.

The Google app, Play Store and Gemini are Google's; nothing is redistributed here.

## Two firmware quirks

Both the China and global `system.img` contain:

```
ProductionTest-release.apk   (factory production test)
app-market-release.apk       (Onyx app market)
```

- **“Hello World”** is a launcher shortcut created from the production-test data
  (`packageName=com.onyx`, `activityClassName=...ResetDeviceDialogActivity`,
  `labelName=Hello World`). It is part of the official firmware's launcher logic, not a
  China leftover. Deleting the launcher row does not stick; the launcher recreates it.
  Removing it permanently requires shadowing/removing the APK (root + Magisk module) or
  editing `system.img` (custom firmware, breaks AVB, OTA overwrites it).
- **Onyx app market** is a China-oriented service. Its endpoints resolve from Europe, but
  the client expects an Onyx account/China region; “network or server error” is common on
  a global ROM outside China. Google Play is the global equivalent. It can be disabled:

```sh
adb shell pm disable-user --user 0 com.onyx.appmarket
```

## OTA

The converted device reports the global `Palma2_Pro_C` fingerprint, so the global OTA
API answers normally. At the time of writing the latest global package was **4.2 build
3316**; 4.3 had not been released for this model. OTA **installation** has not been
verified on the converted unit.
