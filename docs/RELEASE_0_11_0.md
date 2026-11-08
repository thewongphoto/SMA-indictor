# 0.11.0 — centred palette and private iPhone build

## Colour picker

All twelve swatches now sit above the centres of their own labels. The selected
ring remains inside its column on narrow phones. Kivy dispatched new widget
geometry before invalidating cached centre coordinates; drawing now uses the
current position and width directly. Saving a colour still changes that SMA's
chart/title/menu colour and preserves it through restarts and archive/restore.

See the [320/440-wide fixture screenshots](design/ui-0.11.0/README.md).

## iPhone

The first native iPhone target reuses the UI, dividend-adjusted data transport,
persistent SQLite cache, saved-line identities, colours and calculations.
It targets iOS 15+, adds measured safe-area/keyboard bounds, local banners/sound
and Notification Center, and delegates best-effort daily checks to
BGTaskScheduler. Background work rechecks switches, keeps the durable run/event
deduplication and stops further work after native expiry. Relative sandbox
paths keep background configuration usable when iOS moves an app's container
during an update.
Cold background launches avoid importing Kivy or creating an OpenGL window;
only the native task/Python job runs until the app is foregrounded.

The new `ios-v0.11.0` workflow builds device/simulator apps, verifies a small
Xcode signing kit contains the real compiled payload, and checks two fresh
simulator launches with persisted saves. The second launch also includes the
native options Xcode may supply. Failed runs publish diagnostics, not an
installation kit. Native Python/Kivy and the Objective-C bridge use pinned
official sources; HTTPS dependencies are universal Python wheels.

Download **sma-iphone-xcode-kit** after that workflow passes, choose your free
**Personal Team** in Xcode, connect your phone and press Run. Apple credentials
stay on your Mac. Free signing normally needs renewal every seven days.
TestFlight uploads of your own app need paid Apple Developer membership.
See the [complete installation/renewal guide](PRIVATE_IPHONE_INSTALLATION.md).

## Validation and build status

Linux validation: **252 unit tests and 103 distinct running Kivy UI checks**
pass, including palette geometry, storage migration/persistence, iOS adapter
contracts, notification denial/expiry, app-update sandbox relocation, packaging,
mobile HTTPS fixtures and existing Android UI/data regressions. The centred
palette was visually checked at both widths. No user data or uploaded media is
included in screenshots or packages.

This environment is Linux; it cannot run Xcode or sign an iPhone app. Native
compilation/simulator results must be checked in the GitHub Mac workflow.
Personal Team installation, real connectivity and notifications/background
delivery on a physical iPhone remain pending. iOS chooses execution time and
can skip background checks; the Singapore-time targets are not exact alarms.

Android tag: **apk-v0.11.0**. iPhone tag: **ios-v0.11.0**. A pushed tag triggers
the corresponding workflow; it is not proof of a completed APK or iPhone kit.
Android package identity/signing preservation is unchanged. Install the new APK
over the existing app to retain its local saves/cache.
