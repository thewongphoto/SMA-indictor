# iPhone web app

Current web version: **0.18.2**, independently deployable through `main` without
an Android APK tag. See [release scope and parity review](../docs/PLATFORM_RELEASES.md).

Next.js frontend for Safari and Add to Home Screen. Python calculations run
locally using a dedicated Pyodide/NumPy worker and the shared native engine.
Saved parameters, histories and settings stay in IndexedDB. The SVG chart follows
the native viewport, uses shared brand/teal assets, and renders exact Python
crossing pluses and close/SMA touch inspection. Vercel proxies Yahoo
requests and sends Web Push; Supabase provides durable alert state and scheduling.
Normal app opening, optional signup, market lookup and per-device notification
controls need no password. `APP_PASSWORD` and `AUTH_SECRET` protect owner setup
and diagnostics at `/setup/login`; keep existing values in Vercel. Public push
configuration contains only readiness and the VAPID public key, plus an owner
session flag. Device UUIDs remain unguessable capabilities for device operations;
there is no public device-list or shared-library API.

Follow the [beginner setup guide](../docs/PRIVATE_IPHONE_INSTALLATION.md) or open
`/setup` on the deployed website for the seven Vercel variables and prepared SQL.
No persistent Python host is required. The older `web_worker/` mode remains
available only to signed-in owners when both `PYTHON_API_URL` and
`PYTHON_API_TOKEN` are configured. Password-free visitors always use local storage.

Optional signup forwards addresses to the owner through a Vercel function and
Resend. See the [email setup guide](../docs/EMAIL_SIGNUP_SETUP.md) or `/setup/email`.
The current protocol 2 contact SQL stores a private active/removed registry and
source/version history for owner email summaries. Rerun the script when upgrading
from 0.16.0; existing Resend credentials stay unchanged.

```sh
npm ci --prefix web
npm run build --prefix web
npm test --prefix web
```

The build allowlists pure modules from `../sma_analyzer/`, copies the pinned
runtime and downloads its hash-verified numerical wheel from the official
Pyodide CDN. Root Directory stays `web`; allow source files outside it for builds.
Generated `public/python/`, `python-runtime/` and setup copies are ignored by Git.
The lockfile pins all dependencies. Pyodide source/licence notices, NumPy wheel notices, Manrope licences and logo
credits are bundled; see `/THIRD_PARTY_NOTICES.txt`.

Browser validation:

```sh
python -m pip install requests certifi tzdata playwright
python -m playwright install chromium webkit
python -m scripts.smoke_web
python -m scripts.smoke_local_web
python -m scripts.smoke_chart_webkit
python -m scripts.smoke_builder_web
python -m scripts.smoke_setup_feedback
python -m scripts.smoke_signup_web
python -m scripts.smoke_public_access_web
```

The first checks legacy worker compatibility. The second uses actual in-browser
Python with intercepted market fixtures and no Python calculation server.
All mail/push delivery is disabled or mocked in these tests. Browser checks do
not establish physical Safari/iPhone notification behaviour.
