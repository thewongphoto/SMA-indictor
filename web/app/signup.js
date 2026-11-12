"use client";
import { useEffect, useState } from "react";
export default function Signup({ onDone }) {
  const [enabled, setEnabled] = useState(false),
    [email, setEmail] = useState(""),
    [status, setStatus] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    fetch("/api/contact-capabilities")
      .then((response) => response.json())
      .then((value) => setEnabled(value.enabled === true))
      .catch(() => {});
    setEmail(localStorage.getItem("sma-contact-email") || "");
  }, []);
  if (!enabled) return null;
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setStatus("");
    try {
      let id = localStorage.getItem("sma-install-id");
      if (!id) {
        id = crypto.randomUUID();
        localStorage.setItem("sma-install-id", id);
      }
      const response = await fetch("/api/contact-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, install_id: id, platform: "ios-web" }),
      });
      const value = await response.json();
      if (!response.ok || !value.sent)
        throw new Error(
          value.error || "The service has not confirmed your signup.",
        );
      localStorage.setItem("sma-contact-email", email);
      setStatus("Email sent to the developer.");
      onDone?.();
    } catch (error) {
      setStatus(error.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="card">
      <h3>OPTIONAL RELEASE UPDATES</h3>
      <p>
        Leave your email to receive release updates from the developer. Only
        voluntary signups are counted; this is not a total download count.
      </p>
      <form onSubmit={submit}>
        <label>
          Email address
          <input
            type="email"
            autoComplete="email"
            placeholder="name@example.com"
            maxLength="254"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Sending…" : "Save email"}
        </button>
      </form>
      <p role="status">{status}</p>
      {onDone && (
        <button className="text" onClick={onDone}>
          Skip for now
        </button>
      )}
    </section>
  );
}
