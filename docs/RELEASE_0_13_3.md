# 0.13.3 — Android chart-startup build fix

The supplied APK workflow log passed all 332 unit checks, then failed in the
first Kivy UI smoke test before APK compilation:

```text
AttributeError: 'Dataset' object has no attribute 'currency'
```

The 0.13.2 chart comparison assumed live-history metadata was present on every
dataset. The offline preview deliberately uses a smaller fictional Dataset
without a currency field. The chart now accepts absent currency metadata and
shows unlabelled example units rather than assigning a fictitious USD/SGD
denomination. Real histories still display their actual quote currency.

The existing startup smoke test now explicitly checks the comparison amount,
percentage and period for that legacy dataset. Preview tests remain in the
Android workflow alongside live-data fixture tests.

Full UI validation also exposed a timing assumption in the existing scrolling
test: waiting three rendered frames could exceed ScrollView's tap timeout on a
busy software renderer. The test now begins its drag promptly, continues it
over frames and still requires actual page movement. Production scrolling and
touch timeouts are unchanged.

## Release

Validation passed in the Android-host Python 3.11 environment: **332 unit
checks** (two optional NumPy checks skipped), plus all **eight UI workflow
entrypoints**: full offline smoke, library flow, mobile market-data transport,
chart refinements, builder flow, motion/cancellation, slow-clock logo/colour
checks and notification jobs. UI checks used SDL offscreen software rendering
and isolated fixture data. Native APK compilation still runs on GitHub.

The release tag is **apk-v0.13.3**. Source publication triggers the Android
workflow; download the APK only after that workflow succeeds. Install it over
the existing app to retain saved SMAs and cached data. The calculation policy,
package/signing identity and notification schedules are unchanged.

**iOS releases remain paused.** No ios-v0.13.3 tag or iPhone workflow dispatch
is part of this release. The user's planned iPhone route is Vercel.

- [Android build](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml)
- [Installation and request-log guide](YAHOO_ANDROID_TESTING.md)
