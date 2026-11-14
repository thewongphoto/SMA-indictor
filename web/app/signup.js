"use client";
import { useEffect, useRef, useState } from "react";
import packageInfo from "../package.json";
const POINTS = [
  ["Release updates", "The developer emails you when a new version is ready."],
  [
    "A voluntary signup count",
    "Helps count people who choose to sign up. This is not a total download count.",
  ],
  ["Your signup history", "Your address, app source and add/change/remove history are kept privately by the developer for release updates."],
];
export default function Signup({
  onDone,
  onUnavailable,
  variant = "settings",
}) {
  const welcome = variant === "welcome";
  const [enabled, setEnabled] = useState(false),
    [loading, setLoading] = useState(true),
    [email, setEmail] = useState(""),
    [saved, setSaved] = useState(""),
    [status, setStatus] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [accepted, setAccepted] = useState(false),
    [pendingChange, setPendingChange] = useState(null);
  const inFlight = useRef(false);
  const callbacks = useRef({ onDone, onUnavailable });
  callbacks.current = { onDone, onUnavailable };
  useEffect(() => {
    let live = true;
    fetch("/api/contact-capabilities", {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    })
      .then((response) => response.json())
      .then((value) => {
        if (!live) return;
        setEnabled(value.enabled === true);
        if (value.enabled !== true) callbacks.current.onUnavailable?.();
      })
      .catch(() => {
        if (live) callbacks.current.onUnavailable?.();
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    try { setPendingChange(JSON.parse(localStorage.getItem("sma-contact-pending"))); } catch {}
    const stored = localStorage.getItem("sma-contact-email") || "";
    setSaved(stored);
    setEmail(stored);
    if (stored) {
      setAccepted(true);
      setStatus("This email is already saved.");
    }
    return () => {
      live = false;
    };
  }, []);
  async function submit(event) {
    event.preventDefault();
    if (!email.trim() || !event.currentTarget.checkValidity()) {
      setError("Enter a valid email address, like name@example.com.");
      return;
    }
    await sendChange("save", email.trim());
  }
  async function sendChange(operation, value, retry = false) {
    if (inFlight.current) return;
    setError("");
    setStatus("");
    let pending;
    try { pending = JSON.parse(localStorage.getItem("sma-contact-pending")); } catch {}
    if (retry && pending) { operation = pending.operation || "save"; value = pending.email; }
    if (pending && (pending.email !== value || (pending.operation || "save") !== operation)) {
      setError("Retry the pending change before submitting another email change.");
      return;
    }
    if (!pending && operation === "save" && value === saved && localStorage.getItem("sma-contact-protocol") === "2") {
      setAccepted(true); setStatus("This email is already saved."); return;
    }
    inFlight.current = true;
    setBusy(true);
    try {
      let id = localStorage.getItem("sma-install-id");
      if (!id) { id = crypto.randomUUID(); localStorage.setItem("sma-install-id", id); }
      if (!pending) {
        const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
        pending = { email: value, operation, request_id: crypto.randomUUID(), platform: ios ? "ios-web" : "web", version: packageInfo.version };
        localStorage.setItem("sma-contact-pending", JSON.stringify(pending));
      }
      setPendingChange(pending);
      const response = await fetch("/api/contact-email", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...pending, operation, install_id: id, platform: pending.platform || "web", version: pending.version || packageInfo.version }),
        signal: AbortSignal.timeout(55000),
      });
      const result = await response.json();
      if (!response.ok || result.sent !== true) {
        if (result.code === "expired") { localStorage.removeItem("sma-contact-pending"); setPendingChange(null); }
        throw new Error(result.error || "The email change could not be confirmed. Retry, or skip for now.");
      }
      localStorage.removeItem("sma-contact-pending");
      localStorage.setItem("sma-contact-protocol", "2");
      setPendingChange(null);
      if (operation === "remove") {
        localStorage.removeItem("sma-contact-email"); setSaved(""); setEmail(""); setAccepted(false);
        setStatus("Email removed from this app. The developer has been notified.");
      } else {
        localStorage.setItem("sma-contact-email", value); setSaved(value); setEmail(value); setAccepted(true);
        setStatus(result.unchanged ? "This email is already saved." : "Email saved and forwarded to the developer.");
      }
      window.dispatchEvent(new Event("sma-contact-saved"));
    } catch (failure) {
      setError(failure.name === "TimeoutError" || failure.name === "AbortError"
        ? "The email change could not be confirmed. Retry the pending change, or skip for now."
        : failure.message);
    } finally { inFlight.current = false; setBusy(false); }
  }
  if (!enabled) {
    if (welcome && loading)
      return (
        <main className="email-welcome email-loading">
          <img src="/app-icon.png" alt="" />
          <p>Opening SMA Stock Analyzer…</p>
          <button
            className="text"
            onClick={() => callbacks.current.onUnavailable?.()}
          >
            Open the app
          </button>
        </main>
      );
    return null;
  }
  const content = (
    <>
      {welcome ? (
        <>
          <img className="welcome-icon" src="/app-icon.png" alt="" />
          <h1>Welcome to SMA Stock Analyzer</h1>
          <p className="welcome-intro">
            Before you start, you can leave your email. This is all it is used
            for.
          </p>
          <section className="welcome-points">
            {POINTS.map(([title, detail]) => (
              <div key={title}>
                <span className="welcome-dot" />
                <div>
                  <strong>{title}</strong>
                  <p>{detail}</p>
                </div>
              </div>
            ))}
          </section>
        </>
      ) : (
        <>
          <h3>YOUR EMAIL</h3>
          <p>
            Optional release updates. Each addition, change or removal is forwarded
            to the developer with its app source and private signup summary.
          </p>
        </>
      )}
      {accepted ? (
        <section className="email-confirmation" role="status">
          <strong>{status}</strong>
          <p>{saved}</p>
          <button
            className="text"
            disabled={busy}
            onClick={() => {
              setAccepted(false);
              setStatus("");
            }}
          >
            Use a different email
          </button>
        </section>
      ) : (
        <form onSubmit={submit} noValidate>
          <label>
            Email address
            <input
              type="email"
              inputMode="email"
              autoComplete="email"
              placeholder="name@example.com"
              maxLength={254}
              value={email}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? "contact-error" : undefined}
              onChange={(event) => {
                setEmail(event.target.value);
                setError("");
              }}
              disabled={busy}
              required
            />
          </label>
          <button className="primary" disabled={busy}>
            {busy ? "Sending…" : welcome ? "Continue" : "Save email"}
          </button>
        </form>
      )}
      {error && <p id="contact-error" className="negative" role="alert">{error}</p>}
      {!accepted && status && <p role="status">{status}</p>}
      {pendingChange && <button className="text" disabled={busy} onClick={() => sendChange(pendingChange.operation || "save", pendingChange.email, true)}>Retry pending change</button>}
      {saved && <button className="text negative" disabled={busy} onClick={() => sendChange("remove", saved)}>{busy ? "Sending…" : "Remove email"}</button>}
      <p className="small contact-retention">Removing clears this app's saved address and stops its release-update signup. The developer retains the address and removal history in private records and notification emails. Clearing app data or uninstalling cannot send a removal notice.</p>
      {welcome && (
        <footer className="welcome-actions">
          {accepted ? (
            <button
              className="primary"
              onClick={() => callbacks.current.onDone?.()}
            >
              Open the app
            </button>
          ) : (
            <button
              className="text"
              onClick={() => callbacks.current.onDone?.()}
            >
              Skip for now
            </button>
          )}
          <p>You can add, change or remove your email later in Settings.</p>
        </footer>
      )}
      {!welcome && (
        <p className="small">
          Voluntary signups are counted; this is not a total download count.
          Email acceptance does not guarantee inbox delivery.
        </p>
      )}
    </>
  );
  return welcome ? (
    <main className="email-welcome">{content}</main>
  ) : (
    <section className="card email-settings">{content}</section>
  );
}
