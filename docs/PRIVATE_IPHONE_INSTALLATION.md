# Deploy the private iPhone web app

Version 0.14.0 includes a working Next.js frontend in [web/](../web/) and a
persistent Python service in [web_worker/](../web_worker/). Deployment is pending.
This route supports Safari and Add to Home Screen; it does not produce an IPA.
Native iOS releases remain paused.

## 1. Start the Python service on a persistent host

The existing Python engine performs optimization and backtesting. Keep it on a
host with a persistent disk, rather than Vercel's temporary function filesystem.

```sh
python -m venv .venv-web
.venv-web/bin/python -m pip install requests certifi tzdata
export PYTHON_API_TOKEN='replace-with-a-long-random-secret'
.venv-web/bin/python -m web_worker.server --data /persistent/sma-data --port 8100
```

Use a service manager to restart it after host reboots, and an HTTPS reverse
proxy to make it reachable from Vercel. The listener defaults to localhost and
requires a bearer token on every endpoint. Keep that token server-only. Run one
worker process per data directory. Back up that directory privately; it contains
saved parameters and downloaded market histories. Use separate directories and
credentials for testing and production.

The worker is single-user. It uses the Android portable Yahoo HTTPS provider,
the existing 365-day engine, SQLite saved identities and market cache. Pending
calculation jobs are in memory; after a restart the user can run them again.
Saved lines survive worker restarts. A missing deployment or provider outage
produces a visible error rather than sample prices.

## 2. Connect Vercel to GitHub

Import `thewongphoto/SMA-indictor`, select **Next.js**, and set **Root Directory**
to `web`. Use the committed lockfile and `npm run build`. Configure these server
variables in the intended Vercel environment:

| Variable | Purpose |
| --- | --- |
| `APP_PASSWORD` | Private app access password. |
| `AUTH_SECRET` | Long random secret used to sign expiring sessions. |
| `PYTHON_API_URL` | HTTPS origin of the persistent worker. |
| `PYTHON_API_TOKEN` | Same bearer secret as the worker. |

Do not prefix these with `NEXT_PUBLIC_`. Use distinct Preview and Production
credentials. The access cookie is HttpOnly, SameSite Strict and Secure in
production. Mutations reject foreign browser origins. This is private access
for one owner, not a multi-user account or tenant system.

The [web workflow](../.github/workflows/web.yml) builds and runs browser checks;
it does not deploy Vercel. A GitHub push updates a Vercel project only after the
owner has connected and configured that project.

## 3. Open on iPhone

Open the production HTTPS URL in Safari, sign in, then use **Share → Add to Home
Screen**. The app includes a manifest, 192/512px icons, Apple touch icon, safe-area
padding, dynamic viewport sizing and a bottom tab bar that hides while typing.
It supports the shared Home/Charts/Alerts/Settings design, line editing, chart
inspection/pinch, independent backtest ranges and system/light/dark themes.

Downloaded chart snapshots are kept in IndexedDB, and the service worker keeps
the app shell for offline opening. New searches and calculations require a
connection. iOS can evict browser storage; server-side saved parameters remain
on the worker. Clearing downloaded data clears browser snapshots and worker
history without deleting saved parameters. Signing out clears local snapshots.
The Export action downloads saved parameters; native Android data is not
synchronized or imported automatically.

## 4. Optional release-update email

The owner selected **optional signup, enabled only after server configuration**.
Without a configured service, the form is absent and use of the app is unaffected.
On the worker, set all of:

- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`
- `CONTACT_FROM`, `CONTACT_TO`
- Optional `SMTP_PORT` (default 587, mandatory STARTTLS)

The form appears only after the capability endpoint reports that configuration.
The user can skip; submission sends that email and an installation identifier
to the configured developer. Success is shown only after SMTP accepts the mail.
Failures remain visible and can be retried; no silent delivery claim is made.
Rate limits persist on the worker. UI previews disable signup even with SMTP
variables present. No real emails are sent by the automated tests.

For Android, set `SMA_CONTACT_BASE_URL` at runtime during development, or set
`CONTACT_BASE_URL` in [contact.py](../sma_analyzer/contact.py) to the deployed
HTTPS frontend origin before building a subsequent APK. The current APK has no
production URL configured and therefore hides signup. SMTP credentials belong
only on the server. This opt-in feature does not restore retired Gmail/Google
sign-in or email market-alert delivery. Voluntary signups are not total downloads.

## 5. Notifications still require server implementation

The Alerts screen stores per-line preferences and the same three global signal
types as Android. **This web release does not deliver Web Push notifications.**
It says so in the UI and does not offer a misleading permission button.

To enable delivery later, implement durable subscriptions and scheduled market
checks on the server, preserving the shared four SGT job identities and event
deduplication. Web Push needs stable VAPID keys, an HTTPS origin, a push handler
in the service worker and opt-in permission from a user gesture. iPhone supports
web notifications only for eligible Home Screen apps (iOS 16.4+); Safari tabs
need installation guidance. The OS controls notification presentation. Browser
timers cannot replace this scheduler. Android's native scheduler remains active
and unchanged.

## Verification

Run the commands in [web/README.md](../web/README.md). The browser suite uses
synthetic prices and an isolated temporary worker, checks 320/390/768px layouts,
search submission, calculation/save/edit, visibility versus alerts, offline
reopening and archive/restore. Chromium tests are not physical iPhone or Safari
validation. After deployment, check Safari, Add to Home Screen, keyboard/notch
layout, offline reopen and server recovery on the actual phone.
