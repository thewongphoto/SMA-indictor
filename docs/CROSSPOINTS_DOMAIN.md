# Crosspoints website address

The app is named **Crosspoints** from 0.20.0. The current website remains
`https://sma-indictor-xyx2.vercel.app`. The proposed free address is
`https://crosspoints.vercel.app`; Vercel must confirm it is available and assign
it in the owner's account. A public 404 is not proof that a name is available.
The source release does not make this account change.

## Assign the address to the existing project

1. Sign in to [Vercel](https://vercel.com/dashboard) and select the **sma-analyser**
   team, then the existing **sma-indictor-xyx2** project. Do not create a second
   project: this one has the working Git connection, variables and setup.
2. Open **Settings → Domains**. Choose **Add Existing** / **Add Domain** and enter
   `crosspoints.vercel.app` without `https://` or a trailing slash.
3. Connect it to **Production** and confirm. Vercel checks whether the exact name
   can be assigned. If unavailable, choose a different available address such as
   `crosspoints-app.vercel.app`; do not assume any suggested name is free.
4. Retain `sma-indictor-xyx2.vercel.app` on the same project serving Production.
   Do not delete it or redirect its API traffic: installed Android versions use
   its `/api/contact-*` endpoints for optional email changes. No DNS purchase
   or external registrar is needed for a Vercel-owned `.vercel.app` address.
5. Open the new address and confirm it loads Crosspoints and the latest version
   in Settings. **Domains** must show the new assignment is valid.

You can separately rename the dashboard project under **Settings → General →
Project Name → Save**. Renaming the project alone does not establish that the
exact unsuffixed address is available. Preserve the old production alias first;
the immutable project ID retains the Git integration. See Vercel's
[project rename guide](https://vercel.com/kb/guide/how-do-i-change-the-name-of-my-vercel-project)
and [domain settings guide](https://vercel.com/docs/domains/working-with-domains/add-a-domain).

## Move iPhone data and notification setup

Each hostname has separate browser storage and notification permission.
Changing the displayed name at the existing address preserves local data;
opening a different address does not automatically transfer it.

1. In the old app, open **Settings → Saved lines → Export saved parameters**.
   Keep that JSON file privately. Do this before removing an old Home Screen app.
2. At the new address, open **Settings → Saved lines → Import saved parameters**
   and import it. The backup transfers saved parameters/settings, not downloaded
   prices, unsaved archive entries or email-signup/notification identities.
   Histories download again when needed.
3. Open the new address's `/setup/login`, sign in with the existing owner
   `APP_PASSWORD`, then open `/setup`. Use the existing `CRON_SECRET` from Vercel
   in its existing-secret field. Do not generate replacement notification keys.
4. Click **Prepare setup SQL → Copy setup SQL**. Run that prepared script in the
   existing Supabase project's **SQL Editor → New query → Run**. It updates the
   stored website URL and scheduled callbacks while retaining existing records.
5. Return to the new address's `/setup` and click **Check setup**. Confirm it is
   ready and the stored website address matches. If `APP_ORIGIN` or another
   deliberately configured Vercel variable contains the old website address,
   update that URL and redeploy; retain all secrets, VAPID keys and Supabase keys.
6. From Safari, **Share → Add to Home Screen**, naming the icon **Crosspoints**.
   Open that icon, enable notifications in Alerts, allow permission and wait for
   synchronization. Send a test and check the phone. Manage web alerts from the
   new address once the scheduled origin has moved.

An existing Home Screen icon can retain the old installation-time label even
after the website is renamed. Export before replacing it. Optional signup can
be offered again on a new origin because it is a new local app installation.
The original APK data and alert schedules are unaffected by a website alias.

## Email sender display name

The default new owner email sender and subject say **Crosspoints**. If Vercel
has an explicit `CONTACT_FROM`, change only its display name, for example
`Crosspoints <your-existing-verified-sender@example.com>`, and redeploy. Keep the
existing sender address and Resend key. Previously prepared, uncertain email
requests keep their frozen payload when retried to prevent duplicate delivery.
