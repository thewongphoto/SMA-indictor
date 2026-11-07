# UI motion and notification banners

Current Android **0.10.3**, build tag **apk-v0.10.3**. See the
[release notes](RELEASE_0_10_3.md) and [screenshots](design/ui-0.10.3/README.md).

The chart header keeps the saved SMA name and pencil on one row, with the pencil
at the far right. Target crossings appear below the name. Generated period
labels read **SMA (X days)** in cards, charts, saved lines, the archive, guides,
crossing details and alerts. Days mean trading observations, not calendar days.
Custom names, numeric periods and delivery identities are preserved.

Custom target frequencies and custom backtesting years share one rounded dark
numeric field. Backtesting accepts fractional years and keeps the Apply action.
Changing the period does not need a market-data API call.

Pages use a 200ms crossfade with a small directional offset; Back reverses it.
This follows the brief transitions in the supplied reference video. The
recently unsaved archive and both backtesting information sheets share the
Saved SMAs drawer's surface, handle, dimmed backdrop and upward animation.
Tap outside, swipe the handle or use native Back to dismiss. Confirmation and
text-editing dialogs keep their existing keyboard-safe behavior.

Company groups in both saved menus reveal/collapse over 220ms. Hidden controls
cannot receive touches; rapid reversals retain the final chosen state.
Selector menus fade briefly and native Back closes them before leaving a page.

An uncached optimization displays a rotating indicator over a slightly dimmed
modal background. Native Back, or Escape on desktop, cancels it and leaves the
selected company/target visible. No extra on-screen Back button is added.
The worker receives a cancellation event; stale callbacks cannot replace
results or hide a newer overlay. Saved/cached targets still open immediately
without the loading overlay or a price fetch.

The 0.10.3 spinner uses a frame-clock loop rather than a one-shot animation's
unsupported repeat flag. A fixed arc rotates on the GPU; mobile scoring yields
CPU/GIL time periodically so frame updates can continue. Native Back still
cancels promptly without changing optimizer arithmetic. On a saved SMA, the
palette icon left of the rename pencil offers 12 colours, retained through
restart, hiding, unsave/restore and subsequent price refreshes. Automatic colour
allocations remain separate from explicit overrides.

## Android pop-up banners

Research alerts and the manual test request a heads-up banner and sound, then
remain in Android's notification drawer until dismissed or tapped. The app uses
a high-importance **SMA signal alerts** channel. Android cannot raise an existing
channel's importance, so upgrading the old default-importance channel creates
a banner channel. Explicit disabled/quiet choices reported by Android are
retained. An existing banner channel's settings are never overwritten.

Permission, channel settings, Do Not Disturb and device settings control actual
presentation. Use **Test Android phone notification** in Settings. Its result
and the request log explain when a retained quiet channel needs pop-up banners
enabled in Android Settings. Persistent signal/date keys still suppress
duplicates; changing presentation does not replay earlier signals. The
low-priority background-check status notification remains separate.

## Future iOS adapter

`Alert.presentation` requests a banner, sound and retention in Notification
Center without an OS-specific payload. The future iOS adapter must request
alert/sound authorization with `UNUserNotificationCenter`, use the default
notification sound and schedule local requests. Its foreground delegate should
use `.banner`, `.sound` and `.list` on iOS 14+, with `.alert` on earlier supported
versions. iOS handles background presentation. Respect user settings and Focus;
successful posting does not prove that the user saw a banner. Native iOS
scheduling/delivery is still pending and is not tested by Android mocks.

## Automated checks

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m scripts.smoke_ui_motion
```

UI checks use controlled mobile HTTP fixtures and verify intermediate animation
frames, narrow layouts, dismissal, rapid reversals and cancellation races.
Unit checks cover channel migration, OS opt-outs and presentation-independent
delivery keys. Banners, sound, sleeping-phone delivery and iOS presentation
require physical-device testing.

Verified locally: **232 unit tests and 103 distinct UI checks passed**, including 46
general UI checks, 6 library flow, 14 mobile transport, 12 chart refinements,
and 25 colour/logo/motion/flow checks. The existing Android adapter compiles against Android
15 and WorkManager 2.10.1 with the existing p4a service contract. This
compatibility compile uses host stubs and is not a complete APK/device run.
