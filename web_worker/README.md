# Private calculation worker

Run one worker per private user, on a persistent host. It owns SQLite saved
lines, downloaded histories and request logs; do not run it on Vercel's
ephemeral filesystem. The Next.js server forwards authenticated requests with
a server-only bearer token. Do not expose the worker without HTTPS or a private
network. The application is deliberately single-user.

```sh
python -m pip install requests certifi tzdata
export PYTHON_API_TOKEN='a-long-random-server-only-value'
python -m web_worker.server --data /persistent/sma-data --port 8100
```

The default bind address is localhost. Put an HTTPS reverse proxy in front for
Vercel access. Back up the data directory privately. Run only one worker process
for this directory; calculations and provider state are serialized. Calculation
jobs are temporary: a restart retains saved parameters, but the user must rerun
an unfinished calculation. `--preview` is exclusively for synthetic fixtures.

Optional signup requires all of `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`,
`CONTACT_FROM`, `CONTACT_TO`; `SMTP_PORT` defaults to 587 with required STARTTLS.
The capability endpoint enables the form only when all five are present.
The worker sends an explicitly submitted signup to the configured developer,
returns success only after SMTP acceptance, and rate limits repeat submissions.
It does not send market alerts or restore the retired Gmail integration.

See the [full deployment guide](../docs/PRIVATE_IPHONE_INSTALLATION.md).
