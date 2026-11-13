"use client";
import { useEffect, useState } from "react";
import { enablePush, disablePush, syncPush, testPush } from "./push-client";
import { remote } from "./local-service";
export default function PushControls({ push = {}, storage, onChange }) {
  const [config, setConfig] = useState(null),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [installed, setInstalled] = useState(true),
    [runs, setRuns] = useState(null);
  useEffect(() => {
    remote("push/config")
      .then(setConfig)
      .catch((error) => setMessage(error.message));
    const ios =
      /iPad|iPhone|iPod/.test(navigator.userAgent) ||
      (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    setInstalled(
      !ios ||
        matchMedia("(display-mode: standalone)").matches ||
        Boolean(navigator.standalone),
    );
  }, []);
  async function act(action) {
    setBusy(true);
    setMessage("");
    try {
      await action();
      await onChange?.();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }
  if (storage && storage !== "local")
    return (
      <section className="notice">
        <strong>
          Server notifications are not enabled for the legacy worker.
        </strong>
        <p>Switch to local storage to use this phone’s Web Push setup.</p>
      </section>
    );
  return (
    <section className="card">
      <h2>Alerts for this phone</h2>
      {!installed ? (
        <>
          <p>
            On iPhone, open Safari, tap Share → Add to Home Screen, then open
            that app to enable notifications. Requires iOS 16.4 or later.
          </p>
        </>
      ) : !config?.ready ? (
        <>
          <p>
            Finish server setup to receive notifications while the app is
            closed. Local calculations and saved lines work independently.
          </p>
          <a href="/setup">Open notification setup</a>
        </>
      ) : (
        <>
          <p>
            {push.enabled
              ? "Notifications are enabled for this phone. The server checks your synced lines at the scheduled times."
              : "Turn on notifications to receive scheduled research alerts while the app is closed."}
          </p>
          <button
            className="primary"
            disabled={busy}
            onClick={() =>
              act(() => (push.enabled ? disablePush() : enablePush(config)))
            }
          >
            {busy
              ? "Updating…"
              : push.enabled
                ? "Disable notifications"
                : "Enable notifications"}
          </button>
          {push.enabled && (
            <button
              disabled={busy || push.pending}
              onClick={() =>
                act(async () => {
                  await testPush();
                  setMessage(
                    "Test accepted by the push service. Check your phone’s notifications. This does not confirm that a banner appeared.",
                  );
                })
              }
            >
              Send test notification
            </button>
          )}
        </>
      )}
      {push.pending && (
        <p role="status">
          Alert changes are waiting to sync. Reconnect and keep this app open
          until synced.{push.error ? " " + push.error : ""}
          <button disabled={busy} onClick={() => act(syncPush)}>
            Retry sync
          </button>
        </p>
      )}
      {push.last_synced && !push.pending && (
        <p className="small">
          Alert preferences last synced:{" "}
          {new Date(push.last_synced).toLocaleString()}.
        </p>
      )}
      {message && <p role="status">{message}</p>}
      <p className="small">
        iPhone controls notification timing and presentation. Focus settings and
        free-service availability can delay alerts.
      </p>
      {config?.ready && (
        <button
          className="text"
          onClick={() =>
            act(async () => setRuns((await remote("push/status")).runs))
          }
        >
          View recent server checks
        </button>
      )}
      {runs && (
        <div>
          {runs.length ? (
            runs.map((run) => (
              <p key={run.job + run.due}>
                {run.job} · {new Date(run.due).toLocaleString()} · {run.status}{" "}
                · {run.checked} checked / {run.posted} accepted
              </p>
            ))
          ) : (
            <p>No scheduled checks recorded yet.</p>
          )}
        </div>
      )}
    </section>
  );
}
