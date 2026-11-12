# Install and update the Android app

Current source/build tag: **0.13.5 / apk-v0.13.5**. Android builds run on GitHub;
your computer does not need to remain on. A queued or failed run is not an APK.

## Download

1. Sign in to GitHub and open
   [Build Android test APK](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml).
2. Select the run for **apk-v0.13.5**. Wait for a successful result. If you are
   testing an older successful build, record its version instead.
3. Under **Artifacts**, download **sma-android-test** and extract its ZIP.
   Install the `.apk` from the `bin` folder. The other files are diagnostics.
   GitHub's Releases page is not the download location for this workflow.
4. On your Android phone, open the APK from Files/Downloads and allow that app
   to install unknown apps if Android asks. Install **over the existing app**.
5. Open Settings in SMA Stock Analyzer and check **DATA CONNECTION · 0.13.5**.
   If it shows another version, the installed artifact is different.

Keep the same package/signing identity. Do not uninstall or clear app storage
as an update workaround: it can delete saved SMAs and downloaded prices. If
Android reports a signature mismatch, retain the old app and report the error.
[Signing preservation](ANDROID_SIGNING.md) explains the durable key setup.

## First use

The app opens in My SMA library without a selected company or fabricated prices.
Tap New analysis, type Apple/VOO/DBS and press Enter or Submit. Select a matching
company/ETF, choose the target frequency and Optimize SMA. Save with the heart;
use Library or the Saved SMAs drawer to return to exact saved parameters.

Use [the current data/request-log guide](YAHOO_ANDROID_TESTING.md) to check
network calls and persistence, [the app summary](../APP_SUMMARY.md) for chart
and comparison rules, and [the notification guide](ANDROID_DAILY_NOTIFICATIONS.md)
for phone permission, the three signal types and background tests.

No Google login, Gmail authorization or email recipient is required. The new
launcher/launch-screen logo shows the turquoise price crossing above the SMA.

## If the workflow fails

Open its first red step and download the available logs. Share the run URL,
version/tag, failing step and final error. The always-uploaded diagnostic ZIP
may exist even when there is **no APK** inside it. Re-running an old tag uses
that tag's original code, not later fixes on main.

Completed fixes automatically receive a new Android build tag. A manual build
can also be started with **Run workflow → main**. Leave the one-time signing
migration checkbox unchecked except when following the signing guide.

Native iOS releases are paused. For the separate iPhone route, use
[the Vercel/PWA guide](PRIVATE_IPHONE_INSTALLATION.md); an APK cannot install on iPhone.
