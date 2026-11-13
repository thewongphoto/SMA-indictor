# Forward optional signups to your Gmail

Vercel runs the form's server endpoint. Resend delivers each voluntarily
submitted address to **kelwong98@gmail.com**. You do not need another server,
a Gmail password, or Google authorization. The existing Vercel + Supabase
notification setup stays in place.

This feature is optional: **Skip for now** opens the app without submitting an
email. The welcome screen and Settings email card appear only after setup is
complete. Android 0.16.0 uses the same Vercel endpoint as the iPhone web app.

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

This script adds signup counts and protection against repeated/abusive requests.
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

Use **Settings → Your email → Use a different email** to submit a change.
Every newly submitted address change is forwarded too. Submitting the same
already-saved address sends nothing; uncertain retries reuse the same delivery
key. A request older than 23 hours without confirmation must be submitted again
explicitly after the expiry message.

## What is stored and sent

- The address is saved locally on the device after service acceptance and is
  forwarded to your Gmail. Resend processes the message for delivery.
- Supabase stores keyed hashes, timestamps, anonymous installation counts and
  provider acceptance metadata. It stores no email addresses or raw IPs in these
  signup tables. The count measures consenting installations, not all downloads.
- Address changes increase the accepted-submission count, without increasing
  the installation count for that device.
- Server limits are 20 attempts/hour, 80/day and 2,000/month globally, plus five
  per installation and per IP/hour. Retried attempts also use these limits.
  These caps leave headroom under the free plan; check Resend's current limits.
- This forwards signup details only. It does not automatically send release
  campaigns to users, send stock alerts by email, or authorize any other use.

Automated tests mock delivery and send no real emails. Verify a real submission
yourself after adding your key; never share that key to troubleshoot the form.
