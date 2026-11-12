# iPhone web app

Next.js frontend for Safari and Add to Home Screen. It uses the same Python
engine and SQLite saved-line model as Android through a private, persistent
worker. It is not a native iOS package.

See the [deployment guide](../docs/PRIVATE_IPHONE_INSTALLATION.md) for the exact
worker/Vercel setup, optional email signup and remaining notification work.

```sh
npm ci --prefix web
npm run build --prefix web
```

The lockfile pins the tested dependencies. For local development copy
`.env.example` to `.env.local`, fill the four server variables, run the worker,
then `npm run dev --prefix web`. Environment files are excluded from Git.

Browser checks (after a production build):

```sh
python -m pip install playwright
python -m playwright install chromium
python -m scripts.smoke_web
```

The check starts isolated servers on ports 3111 and 8111, uses simulated data
and cannot send signup emails. Screenshots go to `artifacts/web-ui/`.
