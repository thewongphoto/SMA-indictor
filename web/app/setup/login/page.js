"use client";
import { useEffect, useState } from "react";
import { remote } from "../../local-service";

export default function OwnerLogin() {
  const [password, setPassword] = useState(""),
    [owner, setOwner] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    remote("session").then((value) => setOwner(value.owner)).catch(() => {});
  }, []);
  function destination() {
    const next = new URLSearchParams(location.search).get("next");
    return ["/", "/setup", "/setup/email"].includes(next) ? next : "/setup";
  }
  async function login(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await remote("login", { password });
      setPassword("");
      location.assign(destination());
    } catch (failure) {
      setError(failure.message);
      setBusy(false);
    }
  }
  return (
    <main className="login">
      <img src="/app-icon.png" alt="" />
      <h1>Owner server setup</h1>
      <p>The app opens without a password. Only server setup and diagnostics require owner sign-in.</p>
      {owner ? (
        <>
          <p>You are signed in as the owner.</p>
          <button className="primary" onClick={() => location.assign(destination())}>Continue to setup</button>
          <button disabled={busy} onClick={async () => {
            setBusy(true);
            try {
              await remote("logout", {});
              setOwner(false);
              setError("");
            } catch (failure) { setError(failure.message); }
            finally { setBusy(false); }
          }}>Sign out of owner setup</button>
        </>
      ) : (
        <form onSubmit={login}>
          <label>Owner password
            <input type="password" autoComplete="current-password" value={password}
              onChange={(event) => setPassword(event.target.value)} required />
          </label>
          <button className="primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        </form>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      <p><a href="/">Open the app without signing in</a></p>
    </main>
  );
}
