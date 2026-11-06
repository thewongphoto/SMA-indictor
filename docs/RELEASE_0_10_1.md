# 0.10.1 — notification defaults and signal logging

New saved SMAs start with phone notifications **On**. **Buy signal** and
**Impending buy signal** both default to On when no type preference has been
stored. This also works when saving new lines in an older database. Existing
stored Off choices are retained across restarts, repeated saves and archive
restore. Email remains disabled in the app. Android notification permission
is still required.

The scrolling data request log now identifies the ticker, saved SMA name,
period, target frequency, closing date and matching signal. It records checks
with no match, missing closes or switches disabled during retrieval, followed
by explicit signal-trigger and delivery records. Delivery distinguishes OS
acceptance, duplicate suppression and failure. OS acceptance does not mean the
user has seen the alert.

Manual notification tests have separate request, permission-denied, success and
failure records, without claiming a market signal or making a price API call.
The test success message stays visible after refreshing the daily schedule.
Logs survive restart and clearing downloaded prices; raw responses, credentials
and device identifiers remain excluded.

Daily targets stay **US Tue–Sat 06:30 / SGX Mon–Fri 18:30 Asia/Singapore**.
The existing per-market-slot journal and dated delivery keys still suppress
repeat attempts and stale signals. Chart prices, saved identities, custom
names, colors, caches, package and signing configuration are preserved. Desktop
retrieval remains interactive; native iOS background delivery remains separate.

Validation: **212 unit tests and 88 UI checks passed**: 46 general UI,
6 library flow, 14 mobile transport, 12 chart refinements and 10 merged-flow/
notification checks. Automated UI checks use controlled data and mocked OS
delivery. Building the APK, installation/signing verification and sleeping-phone
notification delivery require the GitHub build and physical-device testing.

Build tag: **apk-v0.10.1**. See the
[APK download/request-log guide](YAHOO_ANDROID_TESTING.md) and
[phone notification test guide](ANDROID_DAILY_NOTIFICATIONS.md).
