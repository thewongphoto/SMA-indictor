# Saved lines and notification delivery

Prices remain fictional. The app now includes **native Android local
notifications** and **Gmail API sending**, with Google authorization required.
Preview remains available and never posts or emails anything.

Start with the [beginner Android APK + Gmail setup guide](ANDROID_APK_GUIDE.md).
Read [actual test/build status](ANDROID_TEST_STATUS.md) before expecting an APK.

## Saved lines and channel controls

- The Optimal SMA heart is outlined/grey when unsaved and red when saved for
  that exact period/target. Tapping it again unsaves the configuration.
- The saved-lines bottom sheet opens on a new save or through the bottom-left
  menu. Dismiss it with the menu, downward handle swipe or dimmed-area tap.
- Each row has a chart-matched dash, separate Phone/Email On/Off controls, Hide
  and a red heart. Hiding a line affects its chart visibility, not its alerts.
- The history icon (option A) restores the last ten distinct saved-then-unsaved
  configurations across counters/scenarios, newest first. Older entries are
  discarded. Restore recovers period, target, visibility and channel flags.
- Unsaving stops evaluation of that saved configuration. The current calculated
  overlay may remain visible until its analysis changes.
- The gear opens Screen 3 / Settings. Each channel has independent Buy/Monitor
  switches, defaulting Off. A line's channel **and** its global type must be On.
- Save a valid **recipient** before enabling email on a line. Clearing it is
  blocked while any saved line still has email On. Preferences persist locally.

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

| Type | Phone content / email body first line | Email subject |
| --- | --- | --- |
| Buy | `Buy Signal: DEMO-SGX has crossed above SMA X, target x /year` | `Buy Signal for DEMO-SGX` |
| Monitor | `Monitor: DEMO-SGX has closed below SMA X, target x /year` | `Impending buy signal for DEMO-SGX` |

The saved counter/period/target replace these examples. A second body line labels
SIMULATED DATA, scenario and session. `Preview EOD alerts` displays these exact
subjects and bodies without contacting Gmail or posting a phone notification.

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

## Gmail authorization and sending

The sender is configurable in `sma_analyzer/settings.py`:

```python
GMAIL_SENDER_ADDRESS = "kelwong98@gmail.com"
```

The sender must be a Google account on the phone and must grant permission. The
recipient is the independently saved address in Settings. A sender address alone
cannot grant access or send mail.

`Connect Gmail` invokes Google Identity authorization for only
`https://www.googleapis.com/auth/gmail.send`. The Android OAuth client must match
the installed package and signing SHA-1. No inbox-reading permission, password,
web client secret, Firebase config or custom domain is needed.

The app keeps a short-lived access token in memory only. Google Play services
manages the account grant; the app never persists refresh tokens in SQLite.
An explicit send re-authorizes to obtain a fresh access token, usually without
another consent prompt once granted. `Disconnect` clears the local token and
requests revocation; if offline, revoke access in Google Account settings too.

`Send a test email via Gmail` sends one real, repeatable simulated test to the
saved recipient. `Send enabled alerts` sends matching saved-line emails and phone
alerts. Connecting and previewing send nothing. A failed Gmail connection does
not prevent a valid phone channel from dispatching, or vice versa.

The Gmail REST transport constructs MIME mail, base64url-encodes it and POSTs to
`users/me/messages/send`, with TLS verification using certifi's CA bundle. It
reports API acceptance, expired authorization, configuration/permission errors,
rate limits and uncertain network delivery. API acceptance does not guarantee
inbox placement. There is no automatic retry on a possibly accepted request.

## Deduplication and limits

Successful EOD sends are recorded by data version, channel, type, counter,
scenario, period, target and session. Failed attempts remain retryable. Preview
never changes these records. Clearing app data resets them. A crash/timeout
between provider acceptance and recording can still cause a repeat; check Gmail
**Sent** before retrying an uncertain send. Generic test buttons are deliberately
not deduplicated.

No real account was connected, real email sent or physical phone notification
verified in this cloud session. The native Java/Android build is still awaiting
its first successful GitHub workflow run and device test. The desktop suite
checks the real UI with fake consent, HTTP and Android APIs; see the linked
validation report for exact pass counts and the blocked local build.
