# 0.13.4 — repository and dependency cleanup

The Android/desktop app retains the current real-data features, 365-day policy,
visible-range comparisons, upward-crossing logo and scheduled phone signals.
This release removes the unused Gmail transport/authorization bridge, its
Google sign-in dependency and obsolete spinner validation. Legacy saved-data
fields remain readable; retired email alerts are explicitly blocked at delivery.
Package identity, signing identity, caches and calculation rules are unchanged.

The documentation now has a current index, concise app summary, changelog and
updated install/test guides. Outdated mockups, superseded release diaries,
simulation-only setup and retired rendering scripts were removed. Historical
files remain in Git; [the cleanup record](MAINTENANCE.md) explains what is retained.

## Validation and distribution

Validation passed: **317 unit checks** (two optional NumPy checks skipped),
all **eight Android UI gates**, and **120 local link targets in 29 Markdown
documents**. Tests for deleted Gmail/spinner code were retired; active phone,
legacy-data, calculation and packaging coverage remains. Captures were refreshed
from the controlled 0.13.4 UI run. Fixture checks do not establish native-build
completion or physical-device behaviour.

Only **apk-v0.13.4** is requested. Download from the matching successful
[Android run](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml).
Native iOS releases remain paused; the current
[iPhone guide](PRIVATE_IPHONE_INSTALLATION.md) describes the Vercel/PWA work still needed.
