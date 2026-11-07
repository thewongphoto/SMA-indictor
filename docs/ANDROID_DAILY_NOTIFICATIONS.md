# Daily checks on Android 0.10.3

New saved SMAs default to **Push notifications On**. Both **Buy signal** and
**Impending buy signal** default to On for users without stored type preferences.
Switch either type or an individual SMA off whenever needed. Existing stored
Off choices remain Off after upgrading, reopening, saving the same line again,
or restoring it from the archive; defaults never reset those choices. New saves
also start On in databases created by an older app version. Email remains off.

Both the saved-line switch and a signal type must be on. Hidden chart lines
can still receive alerts. Allow the
Android notification permission when prompted; existing enabled preferences
also trigger one permission request after upgrading. Test notification can
request it again if necessary. A disabled app/channel must be enabled in Android
Settings. Email is not used.

Android 0.10.2 requests pop-up banners and sound before retaining alerts in
the drawer. The [banner/channel guide](UI_MOTION_AND_ALERTS.md#android-pop-up-banners)
explains the upgrade from the old quiet default and preserved OS settings.

| Listing | Singapore-time target | Closing session checked |
| --- | --- | --- |
| US stocks/ETFs | Tuesday–Saturday, 6:30am | Previous US weekday |
| SGX stocks/ETFs | Monday–Friday, 6:30pm | Same Singapore weekday |

These are target times. Android can delay WorkManager jobs during Doze, battery
restrictions or missing connectivity. They are not exact-alarm guarantees.
Normal app backgrounding does not depend on Kivy's event loop remaining active.
Force stopping, disabling or uninstalling the app prevents work; reopen it to
restore scheduling. After a missed slot the job checks the latest eligible
session rather than replaying historical alerts.

At each slot the job re-reads enabled saved SMAs/types, shares one history load
per company, and evaluates their exact saved periods on dividend/split-adjusted
prices. A fresh cache can avoid another HTTP request. It never optimizes or
retunes saved periods. Names appear in alerts without changing deduplication
keys. Switches are checked again after fetching so turning one off during a
request suppresses its alert.

A durable market/slot journal allows one attempt per slot, including network
failures or OS restarts after partial work. Signal/date delivery keys also stop
duplicate notifications. Failed checks are logged and wait for the next slot;
there is no repeated same-slot fetch/retry loop. A missing expected closing date
is logged as **no_new_close** and produces no stale alert. This does not prove
that the date was an exchange holiday.

## Test on the phone

1. Install the **apk-v0.10.3** APK over the existing app, open it and
   allow notifications. Keep saved SMAs and price caches in place.
2. Confirm one saved SMA and a signal type are On. In Settings, use **Test Android phone
   notification** to verify OS permission/channel delivery. This test does not
   consume the daily market slot or call the price API.
3. Press Home, leave connectivity available, and let the phone sleep through a
   scheduled target. Do not use Force stop. A brief **Checking saved SMAs**
   foreground notification may appear during the check.
4. A research alert appears only if its selected rule matches: an upward
   crossing at the latest completed close, or a close strictly below the SMA.
   A successful check with no matching rule sends no research notification.
5. Reopen the app → Settings → **View data request log**. Browse
   `notification-run`, `notification-check`, `notification-trigger` and
   `notification-delivery` rows, alongside actual HTTP/cache rows. Each signal
   entry identifies its ticker, saved SMA name/period, target frequency, closing
   date and **Buy signal** or **Impending buy signal**. Checks show both type
   switches and explain no match, missing close or a switch disabled during
   retrieval. Delivery rows distinguish OS acceptance, duplicate suppression
   and failure. **notification-test** records test requests, permission denial,
   success and failure separately, without claiming a market signal.
   Native startup failures are imported into
   the same log when Settings is opened. Copy the report to share a failure.
6. New cached prices are applied on returning to the app without a further API
   call. The saved name, period and current visibility are retained.

Notification log entries do not represent additional market-data API calls.
An OS-accepted notification means Android accepted the post, not that the user
has seen it. The log persists across restarts and clearing downloaded prices;
use **Load older calls** to reach earlier entries, then **Copy diagnostic report**.

The headless job is portable Python with dated sessions, UTC instants and IANA
timezones. Android's adapter uses WorkManager plus a bounded, separate Python
service process. iOS still requires its native background-task/notification
adapter; its OS does not promise exact scheduled execution either. Desktop has
no background fetcher. Local automated tests do not establish sleeping-phone
delivery; confirm that behavior on the installed APK.
