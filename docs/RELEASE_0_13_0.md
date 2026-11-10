# 0.13.0 — Background notification startup and opening reminders

The supplied 0.10.3 report shows a successful manual notification and a native
scheduler failure before any signal-check rows. Its generic error omits the
underlying exception. This release removes the vulnerable foreground/startService
handoff and adds enough diagnostics to locate any remaining device-specific
failure; it does not claim that the old report identified a particular exception.

## Background execution and diagnostics

Android's regular WorkManager worker now binds a private, dedicated-process
Python service for a bounded job. It requires no Activity or foreground-service
transition. Cancellation releases the binding and signals Python; the next job
waits for the old p4a process to exit. Reports cover provider startup failures,
Python results and cancellation as well as successful signals. Native logs show
the stage, Android API level and cause classes without private error messages.
Imported overnight diagnostics sort by their original event timestamps.

**Settings → Test background notification** queues the same native path for
about ten seconds later. It posts a clearly labelled test without a market API
request or consuming a signal slot. The existing phone test remains available.
See the [step-by-step Android test/log guide](ANDROID_DAILY_NOTIFICATIONS.md).

## Third signal type

**Impending buy signal (Start of trading)** targets **US Monday–Friday 21:30**
and **SGX Monday–Friday 09:00**, fixed Singapore time throughout US daylight
saving changes. It follows the requested condition: the saved SMA is strictly
**below the last adjusted closing price**. The message names the saved SMA and
company, says US/SGX trading is starting soon, and tells the user to monitor
online because the app has no live prices.

The original monitor is renamed **Impending buy signal (End of trading)**;
its close-below-SMA condition is unchanged. Buy/EOD monitoring retain US
Tue–Sat 06:30 and SGX Mon–Fri 18:30 targets. Closing jobs also maintain the cache
for start-only users. Opening jobs need no internet and make no live-price call.
Stale histories and opening jobs more than 30 minutes late are skipped and logged.
A recent closing fetch can verify the latest available older holiday close.

The added type defaults On; stored existing Off choices and per-SMA switches
are preserved. Opening event identities use the upcoming trading date separately
from the reference close. Closing identities/delivery records are retained;
either stage cannot suppress the other. Android and iPhone share these rules,
job identities, preferences and schedules. iOS registers both added BGTask IDs;
its scheduler remains best effort and can skip a narrow opening window.

## Verification and release

Both Python 3.11 build environments pass 301 tests (one desktop-only check
skipped). Tests cover the service entry point without Kivy, sanitized startup
failure reports, cancellation, no-network background tests, duplicate/disabled
rules, stale/holiday close handling, late slots and cross-platform routing.
The actual Android Java sources compile against Android API 35 and WorkManager;
the Java next-run calculation matches the shared Python schedule in 12 DST,
exact-slot and weekend cases. A JVM probe also verifies the actual native
bootstrap-failure writer retains stage/type and excludes the raw exception.
UI checks use controlled HTTP/native fixtures;
they do not establish sleeping-phone delivery.

See [settings screenshots](design/notifications-0.13.0/README.md). Release tags:
**apk-v0.13.0** and **ios-v0.13.0**. Install the Android update over the existing
app and confirm version 0.13.0 before testing. Keep the same signing identity and
iPhone Personal Team/bundle ID. Native build completion still depends on the
GitHub workflows; the iPhone kit still requires local Xcode signing.
