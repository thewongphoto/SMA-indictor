"use client";
import { useEffect, useRef, useState } from "react";
import packageInfo from "../package.json";
const POINTS = [
  ["Release updates", "The developer emails you when a new version is ready."],
  [
    "A voluntary signup count",
    "Helps count people who choose to sign up. This is not a total download count.",
  ],
  ["Nothing else", "Your email is used only for release updates."],
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
    [accepted, setAccepted] = useState(false);
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
    setError("");
    setStatus("");
    const value = email.trim();
    if (!value || !event.currentTarget.checkValidity()) {
      setError("Enter a valid email address, like name@example.com.");
      return;
    }
    if (value === saved) {
      setAccepted(true);
      setStatus("This email is already saved.");
      return;
    }
    setBusy(true);
    try {
      let id = localStorage.getItem("sma-install-id");
      if (!id) {
        id = crypto.randomUUID();
        localStorage.setItem("sma-install-id", id);
      }
      let pending;
      try {
        pending = JSON.parse(localStorage.getItem("sma-contact-pending"));
      } catch {}
      if (!pending || pending.email !== value) {
        pending = { email: value, request_id: crypto.randomUUID() };
        localStorage.setItem("sma-contact-pending", JSON.stringify(pending));
      }
      const response = await fetch("/api/contact-email", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: value,
            install_id: id,
            request_id: pending.request_id,
            platform: "ios-web",
            version: packageInfo.version,
          }),
          signal: AbortSignal.timeout(25000),
        }),
        result = await response.json();
      if (!response.ok || result.sent !== true) {
        if (result.code === "expired")
          localStorage.removeItem("sma-contact-pending");
        throw new Error(
          result.error ||
            "Email acceptance could not be confirmed. Try again, or skip for now.",
        );
      }
      localStorage.setItem("sma-contact-email", value);
      localStorage.removeItem("sma-contact-pending");
      setSaved(value);
      setAccepted(true);
      setStatus("Email saved and forwarded to the developer.");
      window.dispatchEvent(new Event("sma-contact-saved"));
    } catch (failure) {
      setError(
        failure.name === "TimeoutError" || failure.name === "AbortError"
          ? "Email acceptance could not be confirmed. Retry with the same address, or skip for now."
          : failure.message,
      );
    } finally {
      setBusy(false);
    }
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
            Optional release updates. Each new signup or address change is
            forwarded to the developer.
          </p>
        </>
      )}
      {accepted ? (
        <section className="email-confirmation" role="status">
          <strong>{status}</strong>
          <p>{saved}</p>
          <button
            className="text"
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
          {error && (
            <p id="contact-error" className="negative" role="alert">
              {error}
            </p>
          )}
          <button className="primary" disabled={busy}>
            {busy ? "Sending…" : welcome ? "Continue" : "Save email"}
          </button>
        </form>
      )}
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
          <p>You can add or change your email later in Settings.</p>
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
