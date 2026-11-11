# Deploy SMA Stock Analyzer to Vercel for iPhone

Native iOS releases are paused. The new route is an HTTPS web app installed on
an iPhone Home Screen. This needs no Xcode, TestFlight, jailbreak, paid Apple
Developer membership or weekly signing renewal.

**Current status:** this repository contains Python/Kivy, not a deployable web
frontend. It has no web package, manifest or service worker yet. This guide is
the deployment and feature-preservation plan; uploading the unchanged repository
to Vercel will not convert Kivy into a website. No production website is being
created by this documentation update.

## 1. Prepare the web implementation

Use a responsive Next.js frontend on Vercel, with a server-side API, durable
PostgreSQL storage and an authenticated Python calculation/data worker. Reuse
the existing pure Python calculation modules rather than rewriting their rules
without equivalence tests. Long optimizations and scheduled work need a durable
job queue/worker; do not run them in a browser timer or leave a serverless request
running indefinitely. A Vercel Python Function can serve bounded requests, but
its duration, memory and payload limits must be checked against MAX histories.
The persistent worker can be hosted separately from Vercel.

The proposed frontend directory is `web/`; it does not exist yet. Before import,
it must contain a working package.json, build script, responsive pages, API
integration, manifest, icons and service worker. Implement these first, then
follow the dashboard steps below. Account configuration alone cannot provide
feature parity.

| Existing feature | Web implementation required |
| --- | --- |
| Submitted partial ticker/company search | Same-origin authenticated API; search only on Enter/Submit, persistent query cache, bundled company/ETF logos. |
| Real historical prices and MAX | Server-side market requests; retain all available adjusted daily history, dates and quote currency. Validate missing data; dividends/splits are already included, not added twice. |
| Optimized SMA and backtesting | Reuse engine.py, policy.py and backtest.py. Preserve closest annualized frequency per 365 calendar days, warm-up/gap rules, crossing interpolation, DCA interval starts, and the representative modal result from 500 random samples. |
| Chart interaction | Touch-capable chart with two-finger pinch, one-finger EOD inspection, nonoverlapping axes, existing ranges, saved overlays and endpoint currency/% comparisons. |
| Saved library and archive | Grouped accordions, custom names, 12 persistent colours, hearts, visibility, notification switches and restore history. Default groups closed on launch. |
| Guided example | Vanguard S&P 500 ETF (VOO), initial 4/year and Max; adjustable frequency and investment horizon. |
| Loading and cancellation | Shared upward-crossing logo animation; cancellable worker jobs and browser navigation that ignores stale results. |
| Persistent cache | IndexedDB on the phone plus durable server storage; cached browsing after relaunch and explicit cache-clear controls. |
| Background alerts | Server scheduler evaluates saved enabled SMAs and sends visible Web Push notifications; the phone does not run scheduled price fetches while asleep. |
| Request log | Correlated API/cache/job/signal/push records, scrollable and copyable, without tokens, cookies or raw private responses. |

Keep the app private while using the current Yahoo source. A private GitHub
repository does not make a Vercel production URL private. Add application login
and a user allowlist; authorize every API and database operation. Test market
requests from the actual deployed host: cloud IPs can encounter provider blocks
or rate limits even when requests work on Android. Vercel hosting grants no
additional market-data redistribution rights.

## 2. Configure Vercel

Once the web implementation exists:

1. Sign in to Vercel and choose **Add New → Project → Import Git Repository**.
2. Connect GitHub and grant access to `thewongphoto/SMA-indictor`.
3. Select the web implementation branch and set Root Directory to `web/`
   (or its actual directory). Choose Next.js and its package's build defaults.
   Do not point Vercel at the Kivy launcher or Buildozer configuration.
4. Connect a managed database and the calculation worker. Local SQLite files
   and function `/tmp` storage are not durable Vercel application storage.
5. Add the environment variables the implemented backend actually reads.
   Typical names are shown below; they are proposed names, not existing code.
6. Deploy a Preview with test data. Check authentication, APIs and calculations.
7. Set the production branch, deploy Production and choose a stable HTTPS domain
   under Project Settings → Domains. Vercel supplies HTTPS for configured domains.
8. Set production application/auth callback URLs to that final origin, redeploy
   after changing build-time variables, and install that production URL on iPhone.

| Proposed variable | Scope |
| --- | --- |
| NEXT_PUBLIC_APP_URL | Public stable website origin. |
| DATABASE_URL, AUTH_SECRET | Server-only database/auth configuration. |
| PYTHON_API_URL, PYTHON_API_TOKEN | Server-only worker connection. |
| NEXT_PUBLIC_VAPID_PUBLIC_KEY | Public Web Push application key. |
| VAPID_PRIVATE_KEY, VAPID_SUBJECT | Server-only signing key and contact URI. |
| CRON_SECRET | Server-only scheduler endpoint credential. |

Never put database credentials or private VAPID keys in NEXT_PUBLIC variables.
Use separate Preview and Production databases, secrets and job settings.
Previews must not send real alerts. Keep the production origin and VAPID keys
stable: changing origins requires fresh installation/subscription and does not
transfer browser storage automatically.

## 3. Enable the iPhone web-app experience

There is no Vercel switch that enables all iOS features. The frontend must supply:

- A linked web manifest with stable id, name, start_url, scope, standalone display,
  theme/background colours and suitable 192/512px icons from the new logo.
- An Apple touch icon, responsive viewport and safe-area handling for the notch
  and Home indicator; test the keyboard and portrait/landscape layouts.
- A same-origin service worker, normally `/sw.js`, served as JavaScript with
  appropriate update/revalidation headers. Cache the application shell for offline
  opening; do not indiscriminately cache authenticated API responses or secrets.
- IndexedDB for downloaded data and local preferences, and authenticated server
  synchronization for durable saved parameters. Request persistent storage where
  supported, but do not promise it: iOS may evict website data. Provide parameter
  export/import and server recovery. Android's SQLite library does not transfer
  automatically; cross-device sync requires an implemented account/import flow.

On iPhone, open the production URL in **Safari → Share → Add to Home Screen**
(the placement may vary by iOS version), then launch its Home Screen icon.
Use **iOS/iPadOS 16.4 or later** for Home Screen Web Push. A regular Safari tab
alone does not provide the same iPhone push installation context.

Inside the installed app, tap an explicit **Enable notifications** button.
Permission must follow a user gesture. Register the service worker, subscribe
with PushManager and the public VAPID key, and securely save that subscription
on the backend. Handle denied permission and expired subscriptions; the server
must remove invalid endpoints. The worker must display notifications and route
notification taps to the relevant saved SMA. No Apple signing certificate is
required for standards-based Web Push.

## 4. Preserve scheduled signals when the app is closed

WebKit can suspend the page. Background App Refresh, setInterval and a service
worker are not substitutes for a server scheduler. Keep these existing SGT targets:

| Job | Singapore time |
| --- | --- |
| US closing checks | Tuesday–Saturday 06:30 |
| SGX closing checks | Monday–Friday 18:30 |
| US opening reminders | Monday–Friday 21:30, fixed SGT including US DST changes |
| SGX opening reminders | Monday–Friday 09:00 |

Reuse schedule.py and notification rules: closing buy signals use confirmed
upward crossings; closing impending signals use close below SMA. Opening
reminders use SMA strictly below the last eligible adjusted close, include the
existing no-live-prices message, and expire after 30 minutes. Weekday targets
are not proof of an exchange trading day. Verify freshness/reference dates,
avoid duplicate sessions and preserve disabled settings. New SMA/type switches
default on, but iPhone permission is always the user's choice.

Choose a scheduler plan with minute-level dispatch, such as a suitable Vercel
Cron plan or an external scheduler. Check current frequency, precision and usage
limits: do not assume the free Hobby cron offering can meet these targets.
A minutely UTC dispatcher can use schedule.py to find due SGT jobs, atomically
claim each slot in the database and enqueue durable work. Protect its endpoint
with CRON_SECRET; log retries, expiry and deduplication. Do not run alert jobs
on a developer laptop or rely on a function continuing after its response.

The server can check prices while the phone sleeps and send Web Push. iOS,
network availability, Focus and notification settings still control delivery;
exact-time banners cannot be guaranteed. Log push-service acceptance separately
from confirmed user receipt. Refresh the UI from server/cache state on reopening.

## 5. Verify before calling the web release complete

Test on a physical iPhone installed from the production origin:

- Search Apple/VOO/DBS, load genuine adjusted MAX history and inspect request logs.
- Compare optimization/backtest outputs with the existing Python fixtures.
- Test pinch/inspection, all ranges, custom inputs, names, colours and archive.
- Close/reopen and test offline after a first successful load. Verify account
  recovery/export before clearing website data or removing the Home Screen app.
- Enable push through a tap; send a server test with the app foregrounded,
  closed and the phone locked. Inspect both server logs and Notification Center.
- Verify all three signal types, the four schedules, disabled switches,
  duplicates, stale/holiday data and delayed opening-job expiry.
- Deploy an update and roll back it; confirm saved data survives and service
  worker updates do not mix incompatible frontend/API/cache versions.

A successful Vercel deployment establishes hosting, not these acceptance checks.
This documentation change does not implement the web port or trigger native builds.

## Official setup references

Check current platform/plan limits before selecting services:

- https://vercel.com/docs/frameworks/full-stack/nextjs
- https://vercel.com/docs/environment-variables
- https://vercel.com/docs/cron-jobs/usage-and-pricing
- https://vercel.com/docs/functions/limitations
- https://nextjs.org/docs/app/guides/progressive-web-apps
- https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/
- https://developer.mozilla.org/en-US/docs/Web/API/StorageManager/persist

For a previously downloaded native kit only, the historical Xcode instructions
remain in Git history at the ios-v0.13.2 tag. Native releases stay paused.
