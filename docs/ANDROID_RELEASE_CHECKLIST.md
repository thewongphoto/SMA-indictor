# Android regression checklist — run before every test release

This saved checklist tracks the issues reported on **29 October 2026
(Singapore)**. It supplements automated tests; a desktop keyboard or injected
insets do not prove that a phone's IME works correctly.

Record the APK commit/version, signing SHA-1, phone model, Android version,
keyboard app and gesture/three-button navigation mode with each test run.
Use **Pass / Fail / Not tested**, with a short observation. Do not mark an
unexecuted device check as passed.

## Device checks

| ID | Steps | Expected result |
| --- | --- | --- |
| AND-01 | Launch, optimize, open Settings, press native Android Back. Repeat with the full crossover table. | Settings/full table return to Results with the same chart/result. Results returns to Parameters. Only Back on Parameters with no overlay/editor open exits. |
| AND-02 | Open a history/validation popup or saved-lines sheet, then press native Back. | Dismiss the top overlay first; retain the underlying screen. |
| AND-03 | Inspect Settings and expanded saved-SMA groups after installing 0.4.0. | Phone controls remain; email switches, recipient field, Connect Gmail and email-test actions are absent. |
| AND-04 | Tap Test an end-of-day session; enter 273 and then 272. Open/close/reopen the keyboard. Press Preview. | Numeric input remains editable and visible above the keyboard. Preview uses the typed value and sends nothing. Test with DEMO-SGX/Sideways/saved SMA 254 for the documented Buy/Monitor fixtures. |
| AND-05 | Save multiple SMAs for one scenario. On Results tap the menu icon, then close and tap the Saved SMAs text. Scroll the sheet and dismiss by handle, backdrop and native Back. | Both menu targets open the visible list. Every saved row is reachable. Hide/Show and heart remain functional. Chart state is preserved. |
| AND-06 | Save across both fictional counters and multiple scenarios, including a custom target. Return to Parameters or restart. | All saved rows appear below the parameter card, labelled by counter/scenario/period/target. Their action says View. |
| AND-07 | Tap View or a saved row's title on Parameters, including a previously hidden line. | Open Results for that counter/scenario with the exact saved period and target. Selected overlay is visible. No new optimization or silent retuning. Results retains Hide/Show; other saved flags are preserved. |
| AND-08 | Compare all page headings, Back buttons, footer icons and the saved sheet against the phone's status bar/camera cutout/navigation bar. Repeat with the keyboard open. | UI stays within the usable surface; Back/menu/settings controls remain tappable. No duplicate extra padding on Android versions that already inset the SDL surface. |
| AND-09 | Save at least three rows across scenarios, toggle visibility/phone notifications. Force-stop through Android App info, then launch again. | All rows and preferences remain. Launch starts on Parameters and lists all saved rows without optimizing. Test a second restart and reboot if available. Do not clear storage or uninstall during this test. |
| AND-10 | Install the next APK **over** the prior APK and repeat AND-09. | Update installs without a signing mismatch. Same package and SHA-1; previous local data is retained. |
| AND-11 | Build with the durable signing secret present and the disposable cache absent. Compare artifact SHA-1 against the previous successful APK/Google OAuth registration. | SHA-1 is identical. Missing or mismatched signing material must stop the build instead of creating another identity. |
| AND-12 | Press Test Android phone notification; allow permission if requested; check the notification shade and tap the notification. Repeat after denying/disabling the channel. | Native local alert appears with the icon and opens the app. Denial/disabled channel yields a helpful message. No duplicate EOD alert for the same already-delivered event. |
| AND-13 | Update from a prior build with email enabled on saved lines. Preview and send an EOD alert. | Only phone alerts appear/send. Legacy email flags never cause a Google prompt or email dispatch; saved lines remain intact. |

Run AND-03/04/08 on the actual affected phone first. When devices are available,
also test Android 8–10, Android 13+ notification permissions and Android 15+
edge-to-edge behavior, using both gesture and three-button navigation. These
are coverage goals, not claims that those devices have been tested.

## Automated coverage and commands

```sh
python -m unittest discover -s tests -v
python -m scripts.smoke_ui
```

For the focused running Kivy checks:

```sh
python -m scripts.smoke_ui --android-regressions-only
```

Use the headless environment flags in the README when there is no desktop.
The focused checks cover real widget taps, Back dispatch, field focus/text,
injected safe-area/keyboard geometry, saved-menu opening, fresh screen creation
and View. Unit checks include a child process that saves SQLite state and calls
`os._exit(0)` before a new process/store reads it, plus signing restore/fail-closed
policy. Native Java compilation is a separate Android build checkpoint.

## Physical-phone observations

| Build/report | Observation | Status |
| --- | --- | --- |
| User's installed build, reported 29 October 2026 | Test Android phone notification posts successfully | **Pass — user reported** |
| Same report | Native Back exits; email/EOD keyboard disappears; menu/restart discovery fail; UI overlaps status bar | **Fail — reported on previous build** |
| Source version 0.2.1 | Corrections and regression checks implemented | Device retest pending |
| Gmail authorization/real sending | No confirming device result supplied | Not tested |

Install the newly built 0.2.1 APK and fill in AND-01 through AND-13 for that
exact artifact. See [signing preservation](ANDROID_SIGNING.md) before building.
