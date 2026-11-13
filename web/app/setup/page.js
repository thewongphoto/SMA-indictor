"use client";
import { useEffect, useState } from "react";
function base64(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}
export default function Setup() {
  const [existingCron, setExistingCron] = useState("");
  const [config, setConfig] = useState(null),
    [keys, setKeys] = useState(null),
    [message, setMessage] = useState(""),
    [sql, setSql] = useState("");
  async function check() {
    try {
      const response = await fetch("/api/push/config", { cache: "no-store" }),
        value = await response.json();
      if (!response.ok) throw new Error(value.error);
      setConfig(value);
      setMessage("");
    } catch (error) {
      setMessage(error.message);
    }
  }
  useEffect(() => {
    check();
    try {
      const saved = sessionStorage.getItem("sma-generated-keys");
      if (saved) setKeys(JSON.parse(saved));
    } catch {}
  }, []);
  async function generate() {
    if (
      (keys || config?.vapid_ready) &&
      !confirm(
        "Generate new keys? Previously copied keys and SQL must all be replaced together.",
      )
    )
      return;
    const pair = await crypto.subtle.generateKey(
        { name: "ECDSA", namedCurve: "P-256" },
        true,
        ["sign", "verify"],
      ),
      pub = await crypto.subtle.exportKey("raw", pair.publicKey),
      priv = await crypto.subtle.exportKey("jwk", pair.privateKey);
    const value = {
      VAPID_PUBLIC_KEY: base64(pub),
      VAPID_PRIVATE_KEY: priv.d,
      CRON_SECRET: base64(crypto.getRandomValues(new Uint8Array(32))),
    };
    sessionStorage.setItem("sma-generated-keys", JSON.stringify(value));
    setKeys(value);
    setSql("");
  }
  async function prepareSQL() {
    const schedulerSecret = existingCron || keys?.CRON_SECRET;
    if (!schedulerSecret || !/^[A-Za-z0-9_-]{32,}$/.test(schedulerSecret)) {
      setMessage(
        "Use the generated scheduler secret, or paste your existing CRON_SECRET.",
      );
      return;
    }
    const response = await fetch("/setup/supabase.sql");
    if (!response.ok) {
      setMessage("Could not load setup SQL. Reload this page.");
      return;
    }
    const template = await response.text();
    setSql(
      template
        .replaceAll("__APP_URL__", location.origin.replaceAll("'", "''"))
        .replaceAll("__CRON_SECRET__", schedulerSecret),
    );
  }
  async function copy(value) {
    try {
      await navigator.clipboard.writeText(value);
      setMessage(
        "Copied. Paste it only into your own Vercel settings or Supabase SQL Editor.",
      );
    } catch {
      setMessage("Copy was blocked. Select the field and copy it manually.");
    }
  }
  return (
    <main className="setup-page">
      <a href="/">‹ Back to SMA</a>
      <h1>Set up alerts for your iPhone</h1>
      <p>
        Calculations and saved lines stay on this phone. Supabase stores only
        the subscribed alert parameters, push subscription, required
        closing-price snapshots and delivery journal.
      </p>
      {message && <p role="status">{message}</p>}
      <section className="card">
        <h2>1. Check the Supabase connection</h2>
        <p>
          Project:{" "}
          {config?.project_url ||
            "Add SUPABASE_URL and SUPABASE_SECRET_KEY in Vercel, then redeploy."}
        </p>
        <p>
          Sign in on the main app first if this page reports “Sign in to your
          private app.” Keep secret keys out of chat and GitHub.
        </p>
      </section>
      <section className="card">
        <h2>2. Generate notification keys</h2>
        <p>
          Generate once, then keep these values in your password manager. They
          are generated in this browser. This page never reads private keys back
          from Vercel.
        </p>
        <button onClick={generate}>
          {keys ? "Generate replacement keys" : "Generate keys"}
        </button>
        {keys &&
          Object.entries(keys).map(([key, value]) => (
            <label key={key}>
              {key}
              <input
                readOnly
                type={key === "VAPID_PUBLIC_KEY" ? "text" : "password"}
                value={value}
              />
              <button onClick={() => copy(value)}>Copy {key}</button>
            </label>
          ))}
      </section>
      <section className="card">
        <h2>3. Add the three values to Vercel</h2>
        <p>
          Open Vercel → your project → Settings → Environment Variables. Add
          each key and its matching value above, selecting Production. Keep
          APP_PASSWORD, AUTH_SECRET, SUPABASE_URL and SUPABASE_SECRET_KEY.
        </p>
        <p>
          Then open Deployments → the latest production deployment → ⋯ →
          Redeploy. Return to this same browser tab after deployment completes.
        </p>
        <p>
          Do not replace notification keys after subscribing phones unless you
          plan to enable notifications again on each phone.
        </p>
      </section>
      <section className="card">
        <h2>4. Create the database and four scheduled jobs</h2>
        <p>
          Use this page on your production website, not a Vercel preview URL. In
          Supabase, open SQL Editor → New query. Generate and copy the SQL
          below, paste it there, and click Run. The SQL preserves existing alert
          tables and stores the scheduler secret in Supabase Vault.
        </p>
        <label>
          Existing CRON_SECRET (only if you already configured it)
          <input
            type="password"
            autoComplete="off"
            value={existingCron}
            onChange={(event) => setExistingCron(event.target.value)}
          />
        </label>
        <button disabled={!keys && !existingCron} onClick={prepareSQL}>
          Prepare setup SQL
        </button>
        {sql && (
          <>
            <textarea
              readOnly
              aria-label="Supabase setup SQL"
              rows="12"
              value={sql}
            />
            <button onClick={() => copy(sql)}>Copy setup SQL</button>
            <p>
              This filled SQL contains your scheduler secret. Keep it private.
            </p>
          </>
        )}
        <p>
          The four target times are US close: Tue–Sat 06:30; SG close: Mon–Fri
          18:30; US opening reminder: Mon–Fri 21:30; SG opening reminder:
          Mon–Fri 09:00, all Singapore time.
        </p>
      </section>
      <section className="card">
        <h2>5. Check readiness</h2>
        <button onClick={check}>Check setup</button>
        {config && (
          <ul>
            <li>
              Supabase variables:{" "}
              {config.database_configured ? "present" : "missing"}
            </li>
            <li>
              Tables and functions:{" "}
              {config.schema_ready ? "ready" : "run the setup SQL"}
            </li>
            <li>Scheduled jobs: {config.scheduled_jobs} of 4</li>
            <li>
              Notification keys:{" "}
              {config.vapid_ready ? "ready" : "missing or invalid"}
            </li>
            <li>
              Scheduler secret:{" "}
              {config.cron_secret_configured ? "present" : "missing"}
            </li>
            <li>
              Supabase scheduler secret matches Vercel:{" "}
              {config.cron_secret_matches
                ? "yes"
                : "rerun the SQL with the matching generated secret"}
            </li>
            <li>
              Scheduled website URL matches this site:{" "}
              {config.origin_matches
                ? "yes"
                : "prepare and run SQL from your production URL"}
            </li>
          </ul>
        )}
        {config?.ready && (
          <p>
            Server setup is ready. Open your website in Safari → Share → Add to
            Home Screen. Open the installed app → Alerts → Enable notifications
            → Allow, then Send test notification.
          </p>
        )}
      </section>
      <p>
        Free-service quotas, inactive project pausing, market-data availability
        and iPhone settings can delay or prevent alerts. A successful push
        request confirms service acceptance, not that a banner was seen.
      </p>
    </main>
  );
}
