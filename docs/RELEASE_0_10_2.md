# 0.10.2 — UI motion, SMA labels and notification banners

The chart header puts the rename pencil at the far right of the SMA name, with
the target frequency below. Generated periods read **SMA (X days)** across
cards, charts, menus, the archive, guides, crossing details and alerts. Days
mean trading observations. Custom names and numeric saved identities are kept.
Custom backtesting years and target preferences share rounded dark inputs;
fractional backtesting years and Apply remain available.

All six pages use a brief crossfade and small directional offset. Saved-security
groups smoothly expand/collapse in both menus, and selectors fade open/closed.
The unsaved archive and help popups slide up using the Saved SMAs drawer's
surface, handle and dimmed backdrop. They dismiss with the handle, backdrop,
Close or native Back. Opening a drawer ends text editing.

Uncached optimization shows a rotating indicator above a dimmed background.
Native Back cancels it and retains the selected company/target; desktop uses
Escape. Cancellation events stop the worker, and stale callbacks cannot replace
results or dismiss a newer overlay. Saved/cached targets still open immediately.

Research alerts and notification tests request a pop-up banner and sound, then
remain in the notification drawer. A high-importance channel upgrades the old
default channel because Android cannot raise an existing channel's importance.
Explicit OS quiet/disabled choices are retained. Test results and request logs
explain a retained quiet channel. Notification permission, Do Not Disturb and
device settings still control actual presentation. Signal/date deduplication
continues; presentation changes do not replay old signals.

The shared presentation contract records banner, sound and Notification Center
behavior for the future iOS adapter. Native iOS delivery remains separate work.
Android checks remain US Tue–Sat 06:30 / SGX Mon–Fri 18:30 Asia/Singapore.
Desktop remains interactive only. Package, signing configuration, cached prices,
saved periods, names, colors and preferences are preserved.

Validation: **218 unit tests and 97 UI checks passed**: 46 general UI,
6 library flow, 14 mobile transport, 12 chart refinements and 19 motion/flow
checks. Fixtures test intermediate frames, narrow layouts, rapid reversals,
modal dismissal and overlapping canceled workers. Android adapter compatibility
compilation passes against Android 15/WorkManager 2.10.1 with the pinned p4a
service contract and host stubs. These are not full APK or physical-phone tests.
GitHub builds the APK; install it to verify banner/sound and sleeping-phone delivery.

Build tag: **apk-v0.10.2**. See the [screenshots](design/ui-0.10.2/README.md),
[behavior details](UI_MOTION_AND_ALERTS.md),
[APK download guide](YAHOO_ANDROID_TESTING.md) and
[phone notification guide](ANDROID_DAILY_NOTIFICATIONS.md).
