"use client";
import { pushData, remote } from "./local-service";
let sync = Promise.resolve();
function changed() {
  window.dispatchEvent(new Event("sma-push-updated"));
}
function revision(core) {
  core.revision = Math.max(Date.now(), core.revision + 1);
  return core.revision;
}
export function syncPush() {
  sync = sync
    .catch(() => {})
    .then(async () => {
      const { core, persist } = await pushData();
      if (!core.push.enabled && !core.push.disable_pending) return;
      if (
        !navigator.onLine ||
        localStorage.getItem("sma-offline-session") !== "1"
      )
        return;
      try {
        if (core.push.disable_pending) {
          await remote("push/disable", {
            device_id: core.push.device_id,
            revision: core.revision,
          });
          core.push.disable_pending = false;
          core.push.pending = false;
          await persist();
          changed();
          return;
        }
        const permission =
          typeof Notification !== "undefined"
            ? Notification.permission
            : "denied";
        if (permission !== "granted") {
          core.push.enabled = false;
          core.push.disable_pending = true;
          revision(core);
          await persist();
          await remote("push/disable", {
            device_id: core.push.device_id,
            revision: core.revision,
          });
          core.push.disable_pending = false;
          core.push.pending = false;
          await persist();
          changed();
          return;
        }
        const registration = await navigator.serviceWorker.ready,
          subscription = await registration.pushManager.getSubscription();
        if (!subscription) {
          core.push.enabled = false;
          core.push.disable_pending = true;
          revision(core);
          await persist();
          await remote("push/disable", {
            device_id: core.push.device_id,
            revision: core.revision,
          });
          core.push.disable_pending = false;
          core.push.pending = false;
          await persist();
          changed();
          return;
        }
        const lines = core.lines
          .filter((line) => line.push_enabled)
          .map((line) => ({
            ...line,
            region: core.securities[line.counter].region,
            name: core.securities[line.counter].name,
          }));
        if (lines.length > 100)
          throw new Error("Enable up to 100 saved lines for server alerts.");
        const sent = core.revision;
        const result = await remote("push/sync", {
          device_id: core.push.device_id,
          subscription: subscription.toJSON(),
          lines,
          settings: { ...core.settings },
          revision: sent,
        });
        if (result.synced && sent === core.revision) {
          core.push.pending = false;
          core.push.last_synced = new Date().toISOString();
          core.push.error = "";
        }
      } catch (error) {
        core.push.pending = true;
        core.push.error = error.message;
      }
      await persist();
      changed();
    });
  return sync;
}
export async function enablePush(config) {
  if (!config.ready)
    throw new Error("Finish server setup before enabling notifications.");
  if (
    !("serviceWorker" in navigator) ||
    !("PushManager" in window) ||
    !("Notification" in window)
  )
    throw new Error(
      "This browser does not support Web Push. On iPhone, open the installed Home Screen app.",
    );
  const permission = await Notification.requestPermission();
  if (permission !== "granted")
    throw new Error(
      "Notifications were not allowed. Enable them in your phone settings to continue.",
    );
  const registration = await navigator.serviceWorker.ready;
  let subscription = await registration.pushManager.getSubscription();
  const publicBytes = Uint8Array.from(
    atob(config.public_key.replace(/-/g, "+").replace(/_/g, "/")),
    (x) => x.charCodeAt(0),
  );
  if (subscription && subscription.options.applicationServerKey) {
    const existing = new Uint8Array(subscription.options.applicationServerKey);
    if (
      existing.length !== publicBytes.length ||
      existing.some((v, i) => v !== publicBytes[i])
    ) {
      await subscription.unsubscribe();
      subscription = null;
    }
  }
  subscription ||= await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: publicBytes,
  });
  const { core, persist } = await pushData();
  core.push.device_id ||= crypto.randomUUID();
  core.push.enabled = true;
  core.push.pending = true;
  core.push.disable_pending = false;
  revision(core);
  await persist();
  changed();
  await syncPush();
}
export async function disablePush() {
  const { core, persist } = await pushData();
  core.push.enabled = false;
  core.push.pending = true;
  core.push.disable_pending = Boolean(core.push.device_id);
  revision(core);
  await persist();
  changed();
  if ("serviceWorker" in navigator) {
    const registration = await navigator.serviceWorker.ready;
    await (await registration.pushManager.getSubscription())?.unsubscribe();
  }
  await syncPush();
}
export async function testPush() {
  const { core } = await pushData();
  if (core.push.pending)
    throw new Error(
      "Wait for alert preferences to sync before sending a test.",
    );
  return remote("push/test", { device_id: core.push.device_id });
}
