"use client";
import { useEffect, useRef, useState } from "react";
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
  const [checking, setChecking] = useState(false),
    [checkError, setCheckError] = useState(""),
    [needsLogin, setNeedsLogin] = useState(false),
    [checkedAt, setCheckedAt] = useState(null);
  const checkingRequest = useRef(false),
    result = useRef(null);
  async function check(scrollToResult = false) {
    if (checkingRequest.current) return;
    checkingRequest.current = true;
    setChecking(true);
    setCheckError("");
    setNeedsLogin(false);
    setCheckedAt(null);
    try {
      const response = await fetch("/api/push/config", {
          cache: "no-store",
          signal: AbortSignal.timeout(20000),
        }),
        value = await response.json();
      if (!response.ok) {
        setNeedsLogin(response.status === 401);
        throw new Error(value.error || "The setup check could not complete.");
      }
      setConfig(value);
      setCheckedAt(new Date());
    } catch (error) {
      setConfig(null);
      setCheckError(
        error.name === "TimeoutError" || error.name === "AbortError"
          ? "The check timed out. Check your connection and try again."
          : error.message || "The setup check could not complete.",
      );
    } finally {
      checkingRequest.current = false;
      setChecking(false);
      if (scrollToResult)
        requestAnimationFrame(() =>
          result.current?.scrollIntoView({
            block: "nearest",
            behavior: "smooth",
          }),
        );
    }
  }
  const nextStep = !config
    ? ""
    : !config.database_configured
      ? "Add SUPABASE_URL and SUPABASE_SECRET_KEY to this Vercel project's Production variables, then redeploy."
      : !config.vapid_ready || !config.cron_secret_configured
        ? "Complete step 3 above: add the three generated notification values to Vercel Production, then redeploy. Keep your existing keys."
        : !config.schema_ready
          ? "Complete step 4 above: prepare the SQL, paste it into Supabase → SQL Editor → New query, and click Run. If you already ran it, recheck the Supabase secret key in Vercel."
          : !config.cron_secret_matches
            ? "Prepare and run the SQL using the same CRON_SECRET currently saved in Vercel."
            : !config.origin_matches
              ? "Prepare and run the SQL from your production website so its scheduled URL matches this site."
              : config.scheduled_jobs !== 4
                ? "Rerun the prepared SQL to create or activate all four scheduled jobs."
                : "";
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
            (checking
              ? "Checking connection…"
              : checkError
                ? "Connection has not been verified. See the result under Check setup below."
                : "Add SUPABASE_URL and SUPABASE_SECRET_KEY in Vercel, then redeploy.")}
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
        <button disabled={checking} onClick={() => check(true)}>
          {checking ? "Checking setup…" : "Check setup"}
        </button>
        <div
          ref={result}
          className="setup-result"
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          {checking ? (
            <p>
              Checking your Vercel settings and Supabase connection. This can
              take up to 20 seconds.
            </p>
          ) : checkError ? (
            <>
              <p>
                <strong>Setup check could not complete.</strong> {checkError}
              </p>
              {needsLogin ? (
                <p>
                  <a href="/" target="_blank" rel="noopener">
                    Sign in to SMA in a new tab
                  </a>{" "}
                  using your APP_PASSWORD. Then return to this tab and click
                  Check setup again. Your generated keys stay in this tab.
                </p>
              ) : (
                <p>
                  Try Check setup again. If it still fails, share this error
                  message without including any secret values.
                </p>
              )}
            </>
          ) : (
            checkedAt && (
              <>
                <p>
                  <strong>
                    {config?.ready
                      ? "Setup is ready."
                      : "Check complete — setup still needs attention."}
                  </strong>
                </p>
                <p className="small">
                  Last checked: {checkedAt.toLocaleTimeString()}.
                </p>
                {nextStep && (
                  <p>
                    <strong>Next step:</strong> {nextStep}
                  </p>
                )}
              </>
            )
          )}
        </div>
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
