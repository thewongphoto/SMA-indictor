# Saved lines and notification testing

The app still uses fictional prices only. Email is **preview-only**, as requested.
No network sender, live-price API, credentials, backend, background task or APK
has been added. The Android adapter can post **local OS notifications** from a
future Android development build while the app is running. It is not a remote
push service, and it does not monitor prices while the app is closed.

## Hearts and recent history

- The Optimal SMA heart has a grey outline when this exact period/target is
  unsaved, and a red fill when saved. Tap it to save or unsave that configuration.
- Saved lines now live in a partial bottom sheet, opened on a new save or with
  the bottom-left menu on Results. Close it with that menu, a downward swipe on
  its handle, or a tap on the dimmed area. Each saved row has a matching
  chart-colour dash, channel On/Off buttons, a
  compact Hide/Show button at the right, and a red heart furthest right.
- Unsaving a selected line keeps the current calculated overlay available until
  you change it. It stops future alert evaluation for that saved configuration.
- The clock/history icon opens the last **10 distinct unsaved configurations**,
  newest first, across counters and scenarios. Only previously saved lines enter
  this list. Restoring one recovers its period, target, visibility and channel
  settings, and removes it from history. Saving it again also removes its history
  entry. Older entries are discarded when a newer unsave exceeds the ten-entry
  limit; they cannot be restored through the app.
- Saved-line swatches use the same period colour function as the chart. The
  selected period is gold, including all saved targets that share that period.
  Hidden rows retain their colour; hiding one line does not recolour others.

## Test previews on your Mac

1. Open the app, choose a counter/scenario, and press **Optimize SMA**.
2. Tap the outline heart in Optimal SMA to save the result.
3. Press the bottom-right **gear** on Results to open **Notification Settings**.
4. Enter an email address and press **Save**. This saves the recipient locally;
   it does not send an email or verify that the mailbox exists.
5. Turn on the desired Buy signal / Impending buy signal switches under Phone
   and/or Email notifications. They start Off and persist across restarts.
6. Return to Results with Back, then open **Saved SMAs** using the bottom-left
   menu. In **02 / Saved SMA Lines**, turn on Push notifications and/or Email
   notifications for that particular saved line. These controls are independent
   of chart visibility. Turning email on without a saved address opens a helpful
   validation popup with a shortcut to Settings.
7. For a predictable Buy preview, choose a session listed in **03 / Crossovers**
   for the same saved SMA. Close the sheet and use the gear to return to Settings.
   Enter that number in the EOD session field
   and press **Preview EOD alerts**.
8. To test Monitor, choose a session after warm-up whose closing price is strictly
   below that SMA. Equality produces neither a fresh buy nor a monitor alert.

The preview displays the channel, email subject and complete notification text.
Every message is labelled SIMULATED DATA and identifies its scenario and session.
Repeated previews never send messages or mark them delivered. If nothing matches,
the app says so; it does not invent an alert. Invalid sessions show a helpful error.
The default session is 1260; different sessions let you simulate different closes.

Both a saved line's channel and its corresponding global type switch must be On.
All saved lines for the current counter/scenario are evaluated at the requested
close, including hidden lines. Unsaved lines are excluded. Only that close is
evaluated; opening or optimizing the app does not replay five years of alerts.

## Rules and message templates

The Buy rule uses `engine.crossover_events`, including equality retention,
missing-value resets and the full warm-up. The event must land on the requested
EOD session. Monitor means `close < SMA` at that session; no valid close/SMA means
no alert. It can recur on each successive trading session below the SMA.

| Type | Phone content / email body first line | Email subject |
| --- | --- | --- |
| Buy | `Buy Signal: DEMO-SGX has crossed above SMA X, target x /year` | `Buy Signal for DEMO-SGX` |
| Monitor | `Monitor: DEMO-SGX has closed below SMA X, target x /year` | `Impending buy signal for DEMO-SGX` |

Counter, period and target come from the saved line. A second body line identifies
simulated data, scenario and session. These labels do not establish profitability
or promise a price rise. "Impending" is the requested name for a below-SMA close,
not a prediction of a future crossover.

## What the desktop tests verify

Run these inside the project folder with your virtual environment active:

```sh
python -m unittest discover -s tests -v
python -m scripts.smoke_ui
```

The notification unit tests check known upward crossings, equality, missing
values, warm-up, latest-close evaluation, daily monitor keys, channel/type gates,
exact subjects/body templates, email validation, storage migration, the history
limit, restore, failed-delivery retry and successful-delivery deduplication.

The running Kivy tests use the actual heart, history popup, rule switches,
channel buttons, address form and preview/delivery buttons. They inject a fake
Android sender to confirm that Buy/Monitor alerts reach the dispatcher and that
sending the same session twice invokes the sender only once. Email always stays
a preview. Five portrait sizes check swatches, compact right-side actions and
label fit. Screenshots are saved under `artifacts/`.

This verifies app logic and widget connections. It cannot verify Android OS
permissions, device notification rendering, sound, battery restrictions or
background delivery on a Mac/cloud desktop. The desktop **Test Android phone
notification** button explains that an Android development build is required.

## Later physical-phone check — not built in this stage

The user has explicitly deferred completing Android notification integration
and device testing until the Android app build stage. The current adapter is
preparatory; desktop preview/testing is the present workflow.

After Android development packaging is approved:

1. Build with python-for-android/Pyjnius and declare the
   `android.permission.POST_NOTIFICATIONS` manifest permission. Pyjnius is
   imported only on demand, so desktop dependency installation is unchanged.
2. Launch on a physical Android phone and press **Test Android phone notification**.
   On Android 13+, accept the OS permission request, then press the test again.
3. Open the notification shade and confirm the simulated test message.
4. Enable a saved line/type and select a known crossover session. Press
   **Show enabled EOD phone alerts (Android)**; check the message, then press
   again to confirm it is not duplicated. Repeat with a below-SMA session.
5. Deny permission and confirm a helpful failure, then grant permission and retry.

Successful EOD dispatches are recorded locally by dataset version, channel,
notification type, counter, scenario, period, target and session. Failures remain
retryable. This prevents ordinary repeated sends across restarts, but cannot
provide exactly-once delivery if the process crashes after posting and before
recording success. Uninstalling/deleting the database resets these records.
The dedicated generic test button is intentionally repeatable.

Automatic daily operation while closed will need a separate approved design for
genuine EOD arrivals, market calendars/time zones, Android background execution
or a trusted server. The current implementation has no such scheduler.

## Selected email service: Gmail API

The user selected **Gmail API** for future delivery, replacing the Resend
suggestion. Expected volume is at most about 50 messages per month. Sending can
use the user's existing Gmail address; buying or verifying a custom domain is
unnecessary. Account-specific sending limits still apply.

The current app remains **preview-only**. The email address field stores a
recipient, not a connected Google sender. No Gmail account has been connected,
Google Cloud project configured, token requested or email sent.

When delivery is implemented:

1. Enable Gmail API in a Google Cloud project and configure the OAuth consent
   screen and appropriate desktop/Android OAuth clients.
2. Let the user authorize their Google account using Google's supported sign-in
   flow. Request only `https://www.googleapis.com/auth/gmail.send`, which permits
   sending without granting inbox-reading access.
3. Keep refresh/access tokens in secure platform storage, separate from source
   code, screenshots, logs and the ordinary SQLite preferences. Never collect a
   Gmail password in the app or distribute a shared client secret in Android.
4. Connect the existing preview subject/body and deduplication rules to Gmail
   delivery. Test with a fake transport before an explicitly authorized real
   send; provide disconnect/revoke and clear expired-authorization errors.
5. Review OAuth consent/testing status, scope-verification requirements and
   refresh-token lifetime before relying on unattended delivery. Scheduling
   remains a separate task from permission to send an email.

See Google's [Gmail API guide](https://developers.google.com/workspace/gmail/api/guides)
and [authorization scopes](https://developers.google.com/workspace/gmail/api/auth/scopes)
when implementing. This provider decision adds no runtime dependency, network
request, credentials or background work to the present prototype.
