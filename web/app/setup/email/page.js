"use client";
import { useEffect, useState } from "react";
export default function EmailSetup() {
  const [status, setStatus] = useState(null),
    [error, setError] = useState(""),
    [checking, setChecking] = useState(false),
    [sql, setSql] = useState(""),
    [copyStatus, setCopyStatus] = useState("");
  async function check() {
    setChecking(true);
    setError("");
    try {
      const response = await fetch("/api/contact-status", {
          cache: "no-store",
          signal: AbortSignal.timeout(20000),
        }),
        value = await response.json();
      if (!response.ok)
        throw new Error(value.error || "The email setup check failed.");
      setStatus(value);
    } catch (failure) {
      setStatus(null);
      setError(failure.message);
    } finally {
      setChecking(false);
    }
  }
  useEffect(() => {
    check();
  }, []);
  async function prepare() {
    try {
      const response = await fetch("/setup/contact.sql", { cache: "no-store" });
      if (!response.ok) throw new Error("Could not load the email setup SQL.");
      setSql(await response.text());
    } catch (failure) {
      setError(failure.message);
    }
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(sql);
      setCopyStatus(
        "Copied. Paste the script into your Supabase SQL Editor and click Run.",
      );
    } catch {
      setCopyStatus(
        "Copy was blocked. Select the SQL text and copy it manually.",
      );
    }
  }
  return (
    <main className="setup-page">
      <a href="/setup">‹ Back to server setup</a>
      <h1>Set up release-update emails</h1>
      <p>
        Vercel records each email addition, modification or removal and calls Resend to notify{" "}
        <strong>kelwong98@gmail.com</strong>. Gmail is the recipient; no Gmail
        password or Google authorization is needed.
      </p>
      <section className="card">
        <h2>1. Create a free Resend account</h2>
        <p>
          Open{" "}
          <a
            href="https://resend.com/signup"
            target="_blank"
            rel="noopener noreferrer"
          >
            Resend signup
          </a>{" "}
          and register with <strong>kelwong98@gmail.com</strong>. Verify that
          email address.
        </p>
        <p>
          The default sender, onboarding@resend.dev, can send only to the Resend
          account owner. That is sufficient here because every signup is
          forwarded to your own Gmail address. A verified custom domain is
          needed if you later send to other recipients.
        </p>
      </section>
      <section className="card">
        <h2>2. Create an API key</h2>
        <p>
          In Resend → API Keys → Create API Key, name it “SMA signups”. Choose
          Sending access. Copy the key beginning with re_ into your password
          manager. Do not paste it into chat or GitHub.
        </p>
      </section>
      <section className="card">
        <h2>3. Add one Vercel variable</h2>
        <p>
          Open Vercel → sma-indictor-xyx2 → Settings → Environment Variables.
          Add <strong>RESEND_API_KEY</strong>, paste the key as its value, and
          select Production. Save, then redeploy the latest production
          deployment.
        </p>
        <p>
          Keep your existing seven variables and notification keys. The
          recipient is fixed to kelwong98@gmail.com. Optional CONTACT_FROM is
          only for a sender on your own verified Resend domain; leave it unset
          for the default sender.
        </p>
      </section>
      <section className="card">
        <h2>4. Create or upgrade the private signup registry</h2>
        <p>
          Click Prepare email SQL, then copy the complete script. Open your
          existing Supabase project → SQL Editor → New query, paste it, and
          click Run. Rerun this updated script even if email setup worked on
          0.16.0. It adds protocol 2 and a private address/history registry without
          changing your notification jobs or secrets. The registry retains addresses,
          source apps, versions and add/modify/remove history for your email summaries.
          Public app users cannot read the registry. Raw IP addresses are not stored.
        </p>
        <button onClick={prepare}>Prepare email SQL</button>
        {sql && (
          <>
            <textarea
              readOnly
              aria-label="Email setup SQL"
              rows={10}
              value={sql}
            />
            <button onClick={copy}>Copy email SQL</button>
          </>
        )}
        {copyStatus && <p role="status">{copyStatus}</p>}
      </section>
      <section className="card">
        <h2>5. Check email setup</h2>
        <button onClick={check} disabled={checking}>
          {checking ? "Checking email setup…" : "Check email setup"}
        </button>
        <div className="setup-result" role="status">
          {checking ? (
            <p>Checking your configured email service and signup tables…</p>
          ) : error ? (
            <>
              <p>{error}</p>
              <a href="/" target="_blank" rel="noopener">
                Sign in to SMA
              </a>
              <p>
                If sign-in was required, return to this tab and check again.
              </p>
            </>
          ) : (
            status && (
              <>
                <p>
                  <strong>
                    {status.ready
                      ? "Configuration is ready. Submit a signup to verify email acceptance."
                      : "Email signup remains hidden until configuration is complete."}
                  </strong>
                </p>
                <ul>
                  <li>
                    Resend and server variables:{" "}
                    {status.provider_configured
                      ? "present"
                      : "add RESEND_API_KEY and redeploy"}
                  </li>
                  <li>
                    Signup tables/functions:{" "}
                    {status.schema_ready ? "ready — protocol 2" : "rerun the latest email SQL (protocol 2)"}
                  </li>
                  <li>Recipient: {status.recipient}</li>
                  <li>Sender: {status.sender}</li>
                  <li>
                    Voluntary signup installations:{" "}
                    {status.signed_up_installations}
                  </li>
                  <li>
                    Accepted submissions, including changes:{" "}
                    {status.accepted_submissions}
                  </li>
                  <li>Active address records: {status.active_entries || 0}</li>
                  <li>Removed address records: {status.removed_entries || 0}</li>
                  {status.legacy_accepted > 0 && <li>Earlier hash-only submissions: {status.legacy_accepted}. These addresses cannot appear in summaries until those users explicitly save again.</li>}
                </ul>
              </>
            )
          )}
        </div>
      </section>
      <section className="card">
        <h2>6. Open the welcome page</h2>
        <p>
          On the main app, Settings will show Your email when configured. To
          review the welcome screen on this browser, use the link below.
          Continue sends the email; Skip for now opens the app without
          submitting. The form confirms service acceptance, not final inbox
          delivery.
        </p>
        <a href="/?welcome=1">Preview the welcome screen</a>
        <p>
          Check your Gmail inbox and spam folder after a real submission.
          Automated app tests mock delivery and send no real email.
        </p>
      </section>
      <p>
        Signup is optional. Settings offers Use a different email and Remove email.
        Every accepted add/modify/remove sends a notification with its source and app
        version, followed by existing-user and removed-email tables. A replaced address
        appears in the removed table with last change modify. Removal clears the saved
        address on that installation and keeps a private history record. Uninstalling or
        clearing browser/app data cannot send a removal notice. Repeated requests are deduplicated.
        This does not send market alerts by email or automatically send release
        campaigns to users. Form limits protect the free email quota.
      </p>
    </main>
  );
}
