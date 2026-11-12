# Android 0.13.6 notification checks and troubleshooting

Android uses a bounded WorkManager job that binds its private Python service.
The service has a dedicated process, reports native/Python startup failures and
signal outcomes, and stops when the worker releases the binding. It does not
require a foreground Activity or a Kivy timer left running in the background.

## Types, switches and schedules

Each saved SMA's phone switch gates all three global signal-type switches.
Hidden chart lines can still receive alerts. New saved lines and all three types
default On. Existing stored Off choices remain Off; the added opening type takes
its own On default, and can be switched Off independently. Email remains off.

| Type | US listings: Singapore time | SGX listings: Singapore time | Condition |
| --- | --- | --- | --- |
| Buy signal | Tue–Sat 06:30 | Mon–Fri 18:30 | Upward crossing at the latest completed adjusted close |
| Impending buy signal (End of trading) | Tue–Sat 06:30 | Mon–Fri 18:30 | Adjusted close strictly below the saved SMA |
| Impending buy signal (Start of trading) | Mon–Fri 21:30 | Mon–Fri 09:00 | Saved SMA strictly below the last adjusted closing price |

The opening condition follows the requested rule: **last close > SMA**. It is
separate from the end-of-trading condition. Times are fixed in Asia/Singapore,
including US daylight-saving changes; 21:30 is a reminder target, not detection
of an exchange opening. During US standard time it is an hour before the usual
regular-session opening.

The opening message reads, for example:

> US trading is starting soon! SMA (28 days) for Vanguard S&P 500 ETF may cross today. App does not feature live prices, so monitor online.

SG listings use **SGX trading is starting soon!** Saved custom names are included
alongside the numeric SMA. All rules use dividend/split-adjusted prices and exact
saved periods. They never optimize a saved line during a notification check.

## Cache and execution behavior

Closing jobs share one history load per security; a fresh cache can avoid HTTP.
They stay scheduled even for a start-only user so opening reminders have updated
closing data. Opening jobs use the persisted cache and require no network.
They never request intraday/live prices. A stale/unverified older close is
skipped; a fresh closing fetch can establish the latest available close across
a previous weekday holiday. Missing/newer-unexpected dates are logged.

Jobs are unique per absolute slot. Closing identities remain US/SG; opening
identities US_START/SG_START and a separate signal kind prevent either stage
from suppressing the other. Opening delivery keys use the upcoming trading date
and log the previous close separately. Type/line switches are re-read before
posting. The durable run journal and delivery keys suppress repeated work;
failed slots do not enter a repeated fetch/retry loop.

Android can delay WorkManager during Doze, battery restrictions or lack of
connectivity. Opening reminders more than **30 minutes** late are skipped and
logged, rather than announcing an opening hours later. An older queued native
slot cannot borrow today's slot. Schedules are weekday based; the app does not
yet know future exchange holidays. Force stop/disabled apps cannot run work;
reopen the app to restore scheduling. Normal backgrounding uses the native job,
not a paused Kivy timer.

## Test the fixed background path

1. Install **apk-v0.13.6** over the existing app. **Do not uninstall**: retain
   saved SMAs, cached prices and signing identity. Open Settings and confirm
   **DATA CONNECTION · 0.13.6**. View/refresh saved securities to establish
   current closing data; normal closing jobs maintain that cache thereafter.
2. Allow Android notifications. **Test Android phone notification** checks the
   existing foreground/OS notification path. An OS/channel/DND choice still
   controls banners, sound and notification-drawer presentation.
3. Tap **Test background notification**, then press Home. A native worker is
   queued for about ten seconds later, subject to Android scheduling. It binds
   the same headless Python service used by scheduled checks and posts a clearly
   labelled test. **No market API request or trading signal is generated.**
4. Reopen Settings → **View data request log**. Look for native
   `notification-scheduler` started/bound/connected/result rows,
   `notification-service` startup/completion, and
   `notification-test-background` requested/ok/failed. These distinguish a
   scheduling/service failure from permission denial and from no matching rule.
5. Leave a saved live SMA and the intended type On for its next scheduled slot.
   Look for `notification-run`, `notification-check`, `notification-trigger` and
   `notification-delivery`. A successful check with no matching rule posts no
   market notification. Opening rows identify the upcoming day and reference
   close; closing rows identify the completed session and exact saved SMA.
6. If delivery fails, use **Copy diagnostic report** and share the whole report.
   It now includes Android API level, native failure stage/cause classes, or a
   Python startup stage/error class. Raw exception messages, private paths,
   tokens and device identifiers are excluded. Event ordering uses original
   timestamps, including native overnight events imported when the app opens.

Logs survive restarts and clearing downloaded prices. **Load older calls**
retrieves older entries without another API request. OS acceptance confirms a
post, not that a person saw its banner. Local tests use controlled data; validate
sleeping-phone behavior using the installed APK and the new background test.

Native iOS distribution is paused. Its retained adapter is best effort; the
planned browser route needs server scheduling and Web Push instead. See the
[Vercel/iPhone guide](PRIVATE_IPHONE_INSTALLATION.md).
Desktop remains an interactive data/UI test and has no persistent background
fetcher or notification scheduler.
