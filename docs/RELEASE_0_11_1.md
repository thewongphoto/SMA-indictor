# 0.11.1 — Android and iPhone build corrections

The uploaded failed-run logs identified two separate blockers in 0.11.0.

## Android

The sustained-spinner UI check required more than 60 frames in roughly 3.3
seconds. GitHub's software renderer produced **55 frames**, **1,271.91 degrees
of rotation** and a worst update gap of **71.64 ms**. The rotation/continuity
checks passed; the machine-dependent frame-count assertion alone failed, before
the workflow reached signing or APK packaging.

The test now checks more than three rotations, update gaps including the start
and end of the observation, and rotation speed against elapsed time. It still
rejects the old one-revolution stop, mid-run pauses and incorrect clock speed.
A deliberately slow CI clock exercises this during real 6,800-day mobile
scoring. Optional Linux input/clipboard dependencies are installed to remove
unrelated MTDev/xclip warning traces from the logs.

## iPhone

The toolchain's legacy OpenSSL download exhausted five attempts with HTTP 504.
The build now prefetches the pinned OpenSSL 1.1.1w source from the immutable
official Git commit over HTTPS, verifies SHA-256 and populates both host/device
recipe caches. It retries transient transfers, rejects unexpected bytes and
preserves valid legacy release archives. Verified sources are cached before
native compilation. See [source provenance](IOS_NATIVE_SOURCES.md).

This changes source retrieval, not the OpenSSL version, mobile API behavior or
signing route. The centred palette and existing SMA/data behavior are retained.

## Validation and rerun

Validation includes clean Python 3.11 environments matching the workflows'
dependency sets, the exact reported 55-frame regression, real slow-clock Kivy
checks, a live verified source download/cache reuse and source-content comparison
with OpenSSL's official Git release. Native compilation still requires the
GitHub Mac runner; Linux validation does not establish a signed iPhone install.

Use the new build tags **apk-v0.11.1** and **ios-v0.11.1**. Rerunning a 0.11.0
tag uses its old commit. Wait for a successful workflow before downloading
`sma-android-test` or `sma-iphone-xcode-kit`.
