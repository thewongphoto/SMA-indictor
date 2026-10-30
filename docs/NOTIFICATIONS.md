# Saved lines and notification delivery

Version **0.4.0** provides native Android local **phone notifications** only.
Email row controls, settings, recipient editing, Gmail connection and sending
are removed from the application. Legacy stored fields are preserved for upgrades,
but the application's preview and dispatch boundaries ignore the email channel.
Prices and dates remain fictional. Preview sends nothing.

## Saved lines and phone controls

- Both saved libraries group SMAs by security under expandable down/up arrows.
- Each SMA has View, Hide/Show, heart and a Phone notification On/Off control.
- Hiding affects chart visibility, not notification eligibility. Unsaving stops
  evaluation of that configuration; history can restore the last ten unsaved rows.
- Settings has Phone Buy/Monitor switches, defaulting Off. Both the per-line
  control and its global type must be On. Preferences persist locally.

## EOD rules and message templates

Only the selected EOD session is evaluated, for all saved lines in the current
counter/scenario. Opening or optimizing does not replay five years of alerts.

Buy uses `engine.crossover_events`: a strict below-to-above transition, equality
retaining the previous strict side, missing values resetting it, and SMA warm-up
excluded. The event must land on the requested EOD observation.

Monitor means a strictly below-SMA close at that observation. It can recur once
per successive trading session below the SMA. Equality or unavailable close/SMA
produces no Monitor alert. "Impending" is the requested label for this condition,
not a prediction of a future crossover or profit.

| Type | Phone content | Phone title |
| --- | --- | --- |
| Buy | `Buy Signal: DEMO-SGX has crossed above SMA X, target x /year` | `Buy Signal for DEMO-SGX` |
| Monitor | `Monitor: DEMO-SGX has closed below SMA X, target x /year` | `Impending buy signal for DEMO-SGX` |

The saved counter/period/target replace these examples. A second body line labels
SIMULATED DATA, scenario and session. `Preview EOD alerts` displays these exact
phone titles and bodies without posting a notification.

## Android notifications

- Android 13+ requests `POST_NOTIFICATIONS` permission on the Android UI thread.
  The same test action continues after the permission callback grants access.
- A named **SMA research alerts** channel, monochrome chart icon, stable alert ID
  and tap-to-open PendingIntent are provided. Disabled app/channel settings and
  denied permission produce helpful errors and leave failed alerts retryable.
- `Test Android phone notification` is a repeatable generic test. `Send enabled
  alerts` posts eligible EOD alerts and records successful dispatches.
- This is local OS notification delivery, not a remote push service. There is no
  EOD arrival source, daily scheduler or closed-app monitoring in this mock stage.

## Deduplication and limits

Successful EOD sends are recorded by data version, channel, type, counter,
scenario, period, target and session. Failed attempts remain retryable. Preview
never changes these records. Clearing app data resets them. A crash/timeout
between phone dispatch and recording can still cause a repeat. The generic
phone test button is deliberately not deduplicated.

The standalone legacy Gmail modules/tests remain in the repository, but the
application does not instantiate or call them. Their presence does not enable
email in the current app. Current validation and release results are recorded
in ANDROID_TEST_STATUS.md.
