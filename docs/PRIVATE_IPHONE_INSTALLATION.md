# Free iPhone setup: Vercel + Supabase

Version **0.15.0** runs the existing Python SMA/backtest engine on your phone
using Pyodide in a browser worker. Saved lines, settings and downloaded prices
live in IndexedDB. Vercel handles private sign-in, Yahoo HTTPS requests and Web
Push delivery. Supabase stores alert subscriptions, the enabled line parameters,
closing snapshots needed by opening reminders, and the delivery journal.

There is no always-running Python server to rent. Native iOS releases remain
paused. This is the Safari / Add to Home Screen app.

## What you need

- Your GitHub repository connected to a Vercel **Hobby/Free** project.
- A Supabase **Free** project. Free-service quotas and project pausing can stop
  scheduled checks; this setup cannot guarantee uninterrupted or exact-time alerts.
- iOS 16.4+ for Home Screen Web Push, and notification permission on the phone.

## 1. Check your existing Vercel project

In Vercel, open the project → **Settings**:

| Setting | Value |
| --- | --- |
| Git repository | `thewongphoto/SMA-indictor` |
| Production branch | `main` |
| Framework | **Next.js** |
| Root Directory | **`web`** |
| Build Command | Default (`npm run build`) |
| Output Directory | Next.js default; leave override off |
| Install Command | Default npm detection; leave override off |

Allow source files outside the Root Directory in the build settings when that
option is shown: the build bundles the shared engine from `sma_analyzer/`.
The pinned Python runtime and numerical package are copied/downloaded at build
with package hashes checked. No private database or credential file is bundled.

## 2. Add the first four Vercel variables

Open **Settings → Environment Variables**. Each entry has a **Key** (the exact
name below) and a **Value** (your own value). Select **Production** for each.

| Key | Value |
| --- | --- |
| `APP_PASSWORD` | Your chosen website login password. |
| `AUTH_SECRET` | A different random secret of at least 32 characters for sessions. |
| `SUPABASE_URL` | Your project URL, e.g. `https://your-project.supabase.co`. |
| `SUPABASE_SECRET_KEY` | Your Supabase **secret** key, starting `sb_secret_`. |

Find the Supabase key under **Project Settings → API Keys → Secret keys**.
A legacy service-role JWT also works, but a new secret key is preferred.
Do not paste private values into chat, GitHub, screenshots or `NEXT_PUBLIC_`
variables. Supabase requests run on Vercel, not in browser code.

Leave `PYTHON_API_URL` and `PYTHON_API_TOKEN` unset for this local approach.
If those two are both configured, the app deliberately retains the older worker
mode so existing users do not silently lose access to worker-stored parameters.
Export that library before choosing to switch modes; native Android data is not
synchronized automatically.

## 3. Deploy the new code and open notification setup

After the 0.15.0 changes reach GitHub, Vercel should build the connected `main`
branch. Open **Deployments** and wait for **Ready**. If it does not start, choose
**Redeploy** for the latest source deployment. Confirm its commit is current.

Open your production website, sign in using `APP_PASSWORD`, then visit:

```text
https://YOUR-PRODUCTION-WEBSITE/setup
```

For the owner's current deployment:
[open notification setup](https://sma-indictor-xyx2.vercel.app/setup).
If it returns 404, the new source has not finished deploying.

## 4. Generate and save the three notification values

On `/setup`, click **Generate keys** once. Generation happens in your browser.
Save the values in your password manager and keep that browser tab open.

Add these three entries to Vercel → **Settings → Environment Variables**, again
selecting **Production**:

| Key | Value |
| --- | --- |
| `VAPID_PUBLIC_KEY` | The matching generated public key. |
| `VAPID_PRIVATE_KEY` | The matching generated private key. |
| `CRON_SECRET` | The generated scheduler secret. |

There are now **seven variables** in total. The public key is sent to the
browser; the private key and scheduler secret stay server-side.
Optional `VAPID_SUBJECT` can supply your own HTTPS contact URL or `mailto:` URI.

Open **Deployments → latest production deployment → ⋯ → Redeploy** so the
new environment values take effect. Return to the same `/setup` tab afterward.
Do not generate a second set while completing this setup. Replacing VAPID keys
later requires phones to enable notifications again.

## 5. Run the prepared SQL in Supabase

On the production `/setup` page, click **Prepare setup SQL**, then **Copy setup
SQL**. It fills the website URL and scheduler secret locally in your browser.

In Supabase:

1. Open your project.
2. Select **SQL Editor → New query**.
3. Paste the complete prepared script and review it.
4. Click **Run**.

The script creates four tables, protected service-only functions, and four
scheduled jobs. It preserves existing records when rerun. Row Level Security
is enabled and browser `anon`/`authenticated` roles have no table access. The
scheduler secret is stored in **Supabase Vault**, not in the cron job commands.
The filled SQL contains a private secret: do not commit or share it.

If the original setup tab was closed, copy the existing `CRON_SECRET` from your
own Vercel settings into the optional field on `/setup` to prepare the SQL again.
You do not need to replace your notification keys to rerun the SQL.

The unfilled, reviewable template is [web/setup/supabase.sql](../web/setup/supabase.sql).

## 6. Check setup, then enable the iPhone

Back on `/setup`, click **Check setup**. Wait for the result directly beneath
that button (up to 20 seconds). It shows either **Setup is ready**, the next
unfinished step, or an error. If asked to sign in, use the provided new-tab link,
sign in with `APP_PASSWORD`, then return and check again. Keep your generated
keys; there is no need to generate replacements. The checklist checks:

- Supabase variables are configured and the schema/function exists.
- All four jobs are active.
- The notification key formats are valid.
- The scheduler secret in Supabase matches Vercel (compares hashes).
- Supabase's scheduled website URL matches the site you are opening.

When ready:

1. Open your production website in **Safari on the iPhone**.
2. Tap **Share → Add to Home Screen → Add**.
3. Open the new Home Screen icon and sign in.
4. Save an SMA line, then open **Alerts**.
5. Tap **Enable notifications → Allow**.
6. Wait until preferences are synced, then tap **Send test notification**.
7. Inspect the phone's notifications. A server acceptance message alone does
   not prove a banner appeared; iOS/Focus settings control presentation.

A per-line phone switch, that line's signal-type switch and the matching master
switch in Settings must all be enabled. Chart visibility is independent of alerts.
While offline, local changes are saved immediately and marked **waiting to sync**.
Keep the app open after reconnecting until sync succeeds. The server continues
using its last synced preferences until that update arrives.

## Schedules and alert behaviour

All targets stay in **Asia/Singapore**, including US daylight saving changes:

| Job | Singapore-time target | Behaviour |
| --- | --- | --- |
| US close | Tue–Sat 06:30 | Refresh completed adjusted closes; buy crossing / below-line check. |
| SG close | Mon–Fri 18:30 | Same closing check for SG listings. |
| US opening reminder | Mon–Fri 21:30 | Last verified adjusted close strictly above SMA. |
| SG opening reminder | Mon–Fri 09:00 | Same opening reminder for SG listings. |

Supabase pg_cron uses UTC internally. The supplied SQL converts these four
schedules; no paid Vercel Cron schedule is needed. Checks expire after 30 minutes
and do not replay old slots after an outage. Weekday schedules do not invent
an exchange holiday calendar. A closing job only alerts on its expected session;
an opening reminder can use an older close only when the latest closing job
freshly verified that snapshot. Opening jobs do not fetch intraday prices.

Run claims and event keys are stored durably to prevent duplicate checks and
repeated sends. Removed or disabled lines are rechecked before delivery. Expired
push subscriptions are disabled after a 404/410 response. Failed/uncertain sends
are recorded without automatic same-slot replay. View recent results in
**Alerts → View recent server checks**, or the protected Supabase run/event tables.

## Local data and backups

The first calculation downloads roughly a dozen megabytes of Python/runtime
assets; later calculations reuse them. The UI remains responsive and Cancel
terminates the calculation worker. The shared optimizer and backtest modules
retain the native calendar365, warm-up, gap, tie and adjusted-close rules.

After downloading, chart snapshots, the calculation runtime and market histories
can reopen offline. New stock searches and fresh prices still need a connection.
iOS can evict website storage. **Export saved parameters** regularly and keep
the JSON file privately. **Import saved parameters** merges active lines and
settings; existing matching lines keep their current choices. Price histories
and the recently unsaved archive are not included in that backup.

Signing out keeps the local library; clearing downloaded data keeps saved SMA
parameters. Browser data removal can erase both. This is a private single-owner
app, not a multi-user account system or native Android-to-iPhone cloud sync.

## Email and remaining acceptance checks

Optional release-update signup uses Vercel functions and Resend. Follow the
[beginner email setup guide](EMAIL_SIGNUP_SETUP.md), or open `/setup/email` on
your website. Add `RESEND_API_KEY` and run the separate email SQL; keep your seven
notification variables and existing scheduling setup. Signup stays hidden until
configured. Gmail is only the forwarding recipient; no Google authorization or
Gmail password is needed.

The browser suite exercises the real Pyodide runtime and checks results against
Python, offline reload/backtesting, persistence, backup import and setup UI.
Server fixtures compare alert rules/schedules to native Python and verify
concurrent claims, stale closes and expired subscriptions. These checks do not
establish live delivery to a physical iPhone. After completing setup, test a
notification with the Home Screen app closed and inspect the scheduled run log.
