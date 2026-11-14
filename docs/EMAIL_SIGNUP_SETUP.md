# Forward optional signups to your Gmail

Vercel runs the form's server endpoint. Resend delivers each voluntarily
submitted address to **kelwong98@gmail.com**. You do not need another server,
a Gmail password, or Google authorization. The existing Vercel + Supabase
notification setup stays in place.

This feature is optional: **Skip for now** opens the app without submitting an
email. The welcome screen and Settings email card appear only after setup is
complete. Android 0.17.0 uses the same Vercel endpoint as the iPhone web app.

## Upgrading an existing email setup

For **0.17.0**, keep your existing Resend key and Vercel variables. Open
`/setup/email`, prepare/copy the latest SQL, and run it in the same Supabase
project. This upgrades the original hash-only journal to **protocol 2** with a
private address/history registry. Check setup afterwards; the form stays hidden
until the updated schema is ready. Use the updated APK for explicit removals.

Earlier 0.16.0 submissions stored only hashes, so their addresses cannot be
reconstructed for the summary. An existing user can choose **Use a different
email** and save the same prefilled address again to join the new registry.
The app does not submit old addresses automatically on upgrade.

## 1. Create your free Resend account

1. Open [Resend signup](https://resend.com/signup).
2. Register using **kelwong98@gmail.com** and verify that address.
3. Open **API Keys → Create API Key**.
4. Name it **SMA signups**, choose **Sending access**, and create the key.
5. Copy the value beginning with `re_` into your password manager. Do not paste
   it into chat, GitHub, or a public screenshot.

The default sender is `SMA Stock Analyzer <onboarding@resend.dev>`. Resend lets
that sender deliver only to the email address associated with your Resend
account. That works here because every submission goes to your own Gmail.
You need a verified custom domain if you later want to send to other recipients.

## 2. Add one variable in Vercel

1. Open the **sma-indictor-xyx2** project in Vercel.
2. Go to **Settings → Environment Variables → Add Environment Variable**.
3. In **Key**, enter exactly `RESEND_API_KEY`.
4. In **Value**, paste your Resend key. Select **Production**, then **Save**.
5. Go to **Deployments**, open the latest production deployment's **…** menu,
   and choose **Redeploy**. Wait until it says **Ready**.

Keep your seven existing variables: `APP_PASSWORD`, `AUTH_SECRET`,
`SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`,
and `CRON_SECRET`. Keep Root Directory set to **web**.

Leave `CONTACT_FROM` unset to use the default sender. Only set it later to a
sender on your own verified Resend domain. The recipient is fixed in the server
code; users cannot choose a different forwarding destination.

## 3. Run the separate email SQL

1. Open [your email setup page](https://sma-indictor-xyx2.vercel.app/setup/email).
2. Click **Prepare email SQL**, then **Copy email SQL**.
3. Open your existing Supabase project → **SQL Editor → New query**.
4. Paste the complete script and click **Run**.

This script adds the private address registry, source/version/change history,
signup counts and protection against repeated/abusive requests. Rerun it even
if you ran the older 0.16.0 email SQL.
It contains no secret and is safe to rerun. It does not replace your notification
SQL, change notification keys, or recreate scheduled jobs.
The reviewable source is [web/setup/contact.sql](../web/setup/contact.sql).

## 4. Check configuration and send one signup

1. Return to `/setup/email` and click **Check email setup**.
2. If asked to sign in, open the supplied link, sign in with your app password,
   then return and check again.
3. Both **Resend and server variables: present** and **Signup tables/functions:
   ready** should appear. These checks confirm configuration; they do not test
   whether your Resend key can send.
4. Click **Preview the welcome screen**. Enter an address you want to register
   for release updates and press **Continue**.
5. Wait for **Email saved and forwarded to the developer**, then click **Open
   the app**. Check your Gmail inbox and spam folder. Resend's Emails page shows
   delivery status if the email has not appeared.

The form reports provider acceptance, not guaranteed inbox delivery. If Resend
rejects it, check that your account email is the Gmail recipient, your API key
has Sending access, and your sender is the default or a verified domain.
If the form fails, it keeps the address available for retry; Skip still works.

Use **Settings → Your email → Use a different email** to modify an address,
or **Remove email** to remove it from that installation's release-update signup.
Android offers **Save**, **Remove email** and **Retry last change**. Web offers
**Retry pending change** if a request needs confirmation. Removal clears the
saved local address after acceptance and durable recording. Until then, errors
retain the address and request ID so the user can retry without duplicate mail.

## Email format and summary

Each successful change notifies only **kelwong98@gmail.com**, with:

- **Last change:** add, modify or remove.
- Previous/current address, source app, app version and change time in SGT.
- **Existing users:** every tracked active address, with source, version, last
  action, time and installation reference.
- **Removed emails:** replaced/removed addresses with the same details. A replaced
  address has last change **modify**; an explicit removal has **remove**.

The source is automatic: **Android APK**, **iOS web app**, or **Web app**.
These are client labels, not verified device identities. One address can appear
on more than one installation; removing it from Android leaves an iPhone signup
active until it is removed there too. Re-adding an address records **add** again.
The summary is a frozen snapshot of previously accepted changes plus the change
being reported. Concurrent emails can have different snapshots.

Vercel controls the format in [web/lib/contact-message.js](../web/lib/contact-message.js).
Editing/deploying that template updates both platforms. Prepared messages remain
unchanged for retries even if a new template is deployed meanwhile.

## What is stored and sent

- Supabase now retains actual addresses, active/removed status, source app,
  version, last action/time and change history for the owner's summaries. This
  supersedes the hash-only 0.16.0 design. RLS and service-role-only functions
  block public access to the registry; public API responses never contain the lists.
- The app explains that removal keeps a private developer history. Removed
  addresses are historical records and must not be sent release updates. The
  owner also retains copies of notification emails in Gmail/Resend.
- Addresses are saved locally only after acceptance and registry commit.
  Removal clears the local saved address and pending address values. Uninstalling
  or clearing app/browser data cannot send a removal notice; use **Remove email** first.
- Full roster snapshots and prepared message bodies are retained for retries,
  then pruned after 24 hours on subsequent signup activity. Individual event
  details and the active/removed registry remain. Installation IDs and IPs are
  hashed; raw IPs are not stored.
- Submitting an unchanged saved address or an already-removed address sends no
  new email. Uncertain retries reuse the same ID and frozen payload. A pending
  change must be resolved before another one; expired requests require an explicit
  new submission after the expiry message.
- Counts measure consenting installations and accepted changes, not total
  downloads or verified unique people. No automatic release campaigns or stock
  alert emails are sent to users.
- Server limits remain 20 attempts/hour, 80/day and 2,000/month globally, plus
  five per installation and per IP/hour. Retries use these limits too.

Automated tests mock delivery and send no real emails. Verify a real submission
yourself after adding your key; never share that key to troubleshoot the form.
