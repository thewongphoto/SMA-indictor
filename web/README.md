# iPhone web app

Next.js frontend for Safari and Add to Home Screen. Python calculations run
locally using a dedicated Pyodide/NumPy worker and the shared native engine.
Saved parameters, histories and settings stay in IndexedDB. Vercel proxies Yahoo
requests and sends Web Push; Supabase provides durable alert state and scheduling.

Follow the [beginner setup guide](../docs/PRIVATE_IPHONE_INSTALLATION.md) or open
`/setup` on the deployed website for the seven Vercel variables and prepared SQL.
No persistent Python host is required. The older `web_worker/` mode remains
available only when both `PYTHON_API_URL` and `PYTHON_API_TOKEN` are configured.

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
python -m playwright install chromium
python -m scripts.smoke_web
python -m scripts.smoke_local_web
python -m scripts.smoke_setup_feedback
python -m scripts.smoke_signup_web
```

The first checks legacy worker compatibility. The second uses actual in-browser
Python with intercepted market fixtures and no Python calculation server.
All mail/push delivery is disabled or mocked in these tests. Browser checks do
not establish physical Safari/iPhone notification behaviour.
