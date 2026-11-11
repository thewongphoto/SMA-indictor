# 0.13.1 — Crosspoint icon, calendar-year frequency and iPhone build correction

## iPhone failure identified

The supplied 0.13.0 GitHub log shows that the native device app and the local
signing-kit Xcode builds both succeeded. The job then failed in
`scripts/verify_iphone_kit.py` with:

```text
ValueError: Background task identifiers do not match the signed app.
```

The verifier expected only the original US/SG closing jobs. Version 0.13.0 had
correctly added US_START/SG_START, so its four valid identifiers were rejected
by the stale two-identifier check. The corrected build derives expected IDs
from the shared job list. Missing, extra or mismatched IDs still fail verification.
The device build, signing-kit verification and two simulator launches continue
to gate publication of the iPhone kit.

## Selected logo

**Crosspoint (proposal 1)** is now the app-icon design for both Android and
iPhone: navy, a turquoise price line, an orange SMA crossing above it, and a
white plus at the intersection. Platform exports preserve the chosen artwork
and native icon-mask safe areas. The iPhone Personal Team signing kit retains
the compiled icon resources and their metadata.
See the [approved icon preview](design/selected-logo/README.md).

## 365-day frequency definition

For live data, **X/year means the closest historical annualized average of X
upward crossings per 365 observable calendar days**, including weekends and
holidays. It does not guarantee exactly X events in every calendar year.
Warm-up/missing-data exclusions remain. Live yearly chart and backtesting
windows use the same 365-day basis; SMA (X days) continues to mean trading
observations. See [the full calculation note](CALENDAR_YEAR_FREQUENCY.md).

Existing saved SMA periods, names, colours and notification preferences remain
intact. Their displayed frequency is recalculated. New/unsaved optimizations
use the new target objective, while cached choices from the old policy expire.

## Validation

The Android-host and iPhone-host Python 3.11 environments each pass the
319-test suite (two optional desktop/NumPy checks skipped); the desktop
environment passes all 319. Regressions reproduce the exact four-identifier
0.13.0 plist, reject missing/extra jobs, check icon metadata/resource preservation
and asset-catalog linkage, and exercise the actual NumPy calendar scorer without
falling back to the mobile route. Icon checks cover dimensions, opacity,
deterministic exports and Android mask safety. The pinned iOS project template
was rendered and linked with the actual icon master in a local packaging check.

These are fixture/host checks. Native Xcode builds and simulator launches still
run on GitHub's Mac runner; they are required before an iPhone kit is ready.

## Builds and installation

Release tags are **apk-v0.13.1** and **ios-v0.13.1**. Install the Android update
over the existing app. For iPhone, keep the same Personal Team and bundle ID
when signing the new kit. Wait for successful native workflows before downloading
their artifacts. Source/unit validation does not establish physical-device
behavior or Apple signing.

- [Android build and request-log guide](YAHOO_ANDROID_TESTING.md)
- [Free Mac/Xcode iPhone installation](PRIVATE_IPHONE_INSTALLATION.md)
- [Background notification test](ANDROID_DAILY_NOTIFICATIONS.md)
