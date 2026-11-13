import webpush from "web-push";
import { createHash, createECDH } from "node:crypto";
import { database, rpc, readiness } from "./supabase.js";
import { symbolFromKey, historyMarket, dateInZone } from "./market.js";
export const SIGNAL_FIELDS = ["alert_buy", "alert_monitor", "alert_start"];
export function vapidReady() {
  try {
    if (!process.env.VAPID_PUBLIC_KEY || !process.env.VAPID_PRIVATE_KEY)
      return false;
    const pair = createECDH("prime256v1");
    pair.setPrivateKey(Buffer.from(process.env.VAPID_PRIVATE_KEY, "base64url"));
    if (
      pair.getPublicKey().toString("base64url") !== process.env.VAPID_PUBLIC_KEY
    )
      return false;
    webpush.setVapidDetails(
      process.env.VAPID_SUBJECT ||
        process.env.APP_ORIGIN ||
        "https://sma-indictor-xyx2.vercel.app",
      process.env.VAPID_PUBLIC_KEY,
      process.env.VAPID_PRIVATE_KEY,
    );
    return true;
  } catch {
    return false;
  }
}
export async function pushConfig(origin) {
  const status = await readiness(),
    { cron_secret_sha256: storedHash, ...publicStatus } = status;
  const configured = Boolean(process.env.CRON_SECRET?.length >= 32),
    matches =
      configured &&
      storedHash ===
        createHash("sha256").update(process.env.CRON_SECRET).digest("hex");
  const originMatches = !origin || status.app_url === origin;
  return {
    ...publicStatus,
    vapid_ready: vapidReady(),
    cron_secret_configured: configured,
    cron_secret_matches: matches,
    origin_matches: originMatches,
    public_key: process.env.VAPID_PUBLIC_KEY || "",
    project_url: process.env.SUPABASE_URL || "",
    ready:
      status.schema_ready &&
      status.scheduled_jobs === 4 &&
      vapidReady() &&
      matches &&
      originMatches,
  };
}
export function deviceId(value) {
  if (
    typeof value !== "string" ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
      value,
    )
  )
    throw new Error("Invalid device identifier");
  return value;
}
export function subscription(value) {
  if (
    !value ||
    typeof value.endpoint !== "string" ||
    value.endpoint.length > 2048
  )
    throw new Error("Invalid push subscription");
  const url = new URL(value.endpoint),
    host = url.hostname;
  if (
    url.protocol !== "https:" ||
    url.port ||
    url.username ||
    url.password ||
    !(
      host === "web.push.apple.com" ||
      host.endsWith(".push.apple.com") ||
      host === "fcm.googleapis.com" ||
      host.endsWith(".push.services.mozilla.com")
    )
  )
    throw new Error("Unsupported push service endpoint");
  if (
    !/^[A-Za-z0-9_-]{80,120}$/.test(value.keys?.p256dh || "") ||
    !/^[A-Za-z0-9_-]{20,32}$/.test(value.keys?.auth || "")
  )
    throw new Error("Invalid subscription encryption keys");
  return {
    endpoint: url.href,
    keys: { p256dh: value.keys.p256dh, auth: value.keys.auth },
  };
}
export function cleanDevice(body) {
  const id = deviceId(body.device_id);
  const revision = body.revision;
  if (
    !Number.isSafeInteger(revision) ||
    revision < 0 ||
    !Array.isArray(body.lines) ||
    body.lines.length > 100
  )
    throw new Error("Sync up to 100 alert lines with a valid revision.");
  const settings = {};
  for (const key of ["phone_buy", "phone_monitor", "phone_monitor_start"]) {
    if (typeof body.settings?.[key] !== "boolean")
      throw new Error("Invalid signal settings");
    settings[key] = body.settings[key];
  }
  const lines = body.lines.map((line) => {
    const symbol = symbolFromKey(line.counter),
      region = symbol.endsWith(".SI") ? "SG" : "US";
    if (
      line.region !== region ||
      !Number.isSafeInteger(line.period) ||
      line.period < 2 ||
      line.period > 100000 ||
      !Number.isSafeInteger(line.target_frequency) ||
      line.target_frequency < 1 ||
      typeof line.custom_name !== "string" ||
      line.custom_name.length > 60 ||
      /[\u0000-\u001f\u007f]/.test(line.custom_name)
    )
      throw new Error("Invalid saved alert line");
    const result = {
      counter: line.counter,
      symbol,
      region,
      period: line.period,
      target_frequency: line.target_frequency,
      custom_name: line.custom_name,
      name: String(line.name || symbol).slice(0, 160),
    };
    for (const key of SIGNAL_FIELDS) {
      if (typeof line[key] !== "boolean")
        throw new Error("Invalid line signal type");
      result[key] = line[key];
    }
    return result;
  });
  return {
    p_id: id,
    p_revision: revision,
    p_subscription: subscription(body.subscription),
    p_settings: settings,
    p_lines: lines,
  };
}
export async function syncDevice(body) {
  const clean = cleanDevice(body);
  if (!vapidReady()) throw new Error("Notification keys are not configured.");
  const applied = await rpc("sma_sync_device", clean);
  return { synced: applied, revision: clean.p_revision };
}
export async function disableDevice(body) {
  const id = deviceId(body.device_id);
  if (!Number.isSafeInteger(body.revision)) throw new Error("Invalid revision");
  await database(`sma_push_devices?id=eq.${id}&revision=lte.${body.revision}`, {
    method: "PATCH",
    body: {
      enabled: false,
      revision: body.revision,
      updated_at: new Date().toISOString(),
    },
  });
  return { disabled: true };
}
export async function sendPush(device, payload) {
  if (!vapidReady()) throw new Error("Notification keys are not configured.");
  return webpush.sendNotification(
    subscription(device.subscription),
    JSON.stringify(payload),
    { TTL: 1800, timeout: 10000, urgency: "normal" },
  );
}
export async function testPush(body) {
  const id = deviceId(body.device_id),
    devices = await database(
      `sma_push_devices?id=eq.${id}&enabled=eq.true&select=*`,
    );
  if (!devices.length)
    throw new Error("Enable notifications for this phone first.");
  await sendPush(devices[0], {
    title: "SMA test notification",
    body: "The server accepted this test for delivery. iPhone notification settings control its presentation.",
    url: "/",
  });
  return { accepted: true };
}
// Weekday targets intentionally do not invent exchange holiday calendars.
const specs = {
  US: { minutes: 390, days: [2, 3, 4, 5, 6] },
  SG: { minutes: 1110, days: [1, 2, 3, 4, 5] },
  US_START: { minutes: 1290, days: [1, 2, 3, 4, 5] },
  SG_START: { minutes: 540, days: [1, 2, 3, 4, 5] },
};
export function latestDue(job, now = Date.now()) {
  const spec = specs[job];
  if (!spec) throw new Error("Unknown notification job");
  const local = dateInZone(now, "Asia/Singapore");
  const midnight = Date.parse(local.date + "T00:00:00+08:00");
  for (let day = 0; day < 8; day++) {
    const due = midnight - day * 86400000 + spec.minutes * 60000,
      weekday = new Date(due + 8 * 3600000).getUTCDay();
    if (spec.days.includes(weekday) && due <= now) return due;
  }
  throw new Error("No current slot");
}
export function expectedDate(job, due) {
  const date = dateInZone(due, "Asia/Singapore").date,
    stamp = Date.parse(date + "T12:00:00Z");
  if (job.endsWith("_START")) {
    let previous = stamp - 86400000;
    while ([0, 6].includes(new Date(previous).getUTCDay()))
      previous -= 86400000;
    return new Date(previous).toISOString().slice(0, 10);
  }
  return new Date(stamp - (job === "US" ? 86400000 : 0))
    .toISOString()
    .slice(0, 10);
}
export function evaluateSignal(data, line, settings, start = false) {
  // Same rolling order, equality handling, missing-window resets and strict comparisons as Python.
  const period = line.period,
    prices = data.prices;
  if (period > prices.length) return null;
  let total = 0,
    run = 0,
    previousSide = null,
    average = null,
    crossing = false;
  for (let i = 0; i < prices.length; i++) {
    const value = prices[i];
    crossing = false;
    if (!Number.isFinite(value)) {
      total = 0;
      run = 0;
      previousSide = null;
      average = null;
      continue;
    }
    total += value;
    run++;
    if (run > period) total -= prices[i - period];
    if (run < period) {
      average = null;
      continue;
    }
    average = total / period;
    if (!Number.isFinite(average)) {
      previousSide = null;
      continue;
    }
    const side = value > average ? 1 : value < average ? -1 : 0;
    if (side) {
      crossing = previousSide === -1 && side === 1;
      previousSide = side;
    }
  }
  const last = prices.at(-1);
  if (!Number.isFinite(last) || !Number.isFinite(average)) return null;
  if (start)
    return settings.phone_monitor_start && line.alert_start && last > average
      ? "monitor_start"
      : null;
  if (crossing && settings.phone_buy && line.alert_buy) return "buy";
  return last < average && settings.phone_monitor && line.alert_monitor
    ? "monitor"
    : null;
}
export async function runAlerts(
  job,
  {
    now = Date.now(),
    db = database,
    call = rpc,
    history = historyMarket,
    send = sendPush,
  } = {},
) {
  const due = latestDue(job, now),
    start = job.endsWith("_START"),
    region = job.startsWith("US") ? "US" : "SG";
  if (now - due > 1800000) return { status: "expired", checked: 0, posted: 0 };
  const dueISO = new Date(due).toISOString(),
    expected = expectedDate(job, due);
  if (!(await call("sma_claim_run", { p_job: job, p_due: dueISO })))
    return { status: "already_checked", checked: 0, posted: 0 };
  const started = Date.now();
  let checked = 0,
    posted = 0,
    failed = false;
  try {
    const devices = await db("sma_push_devices?enabled=eq.true&select=*");
    const relevant = devices.filter(
      (d) =>
        Date.parse(d.created_at) <= due &&
        d.lines.some(
          (l) =>
            l.region === region &&
            (start
              ? d.settings.phone_monitor_start && l.alert_start
              : (d.settings.phone_buy && l.alert_buy) ||
                (d.settings.phone_monitor && l.alert_monitor) ||
                (d.settings.phone_monitor_start && l.alert_start)),
        ),
    );
    const counters = [
      ...new Set(
        relevant.flatMap((d) =>
          d.lines.filter((l) => l.region === region).map((l) => l.counter),
        ),
      ),
    ];
    const histories = new Map();
    for (const counter of counters) {
      if (Date.now() - started > 45000) {
        failed = true;
        break;
      }
      try {
        if (start) {
          const rows = await db(
            "sma_alert_history?counter=eq." +
              encodeURIComponent(counter) +
              "&select=*",
          );
          const cached = rows[0];
          if (cached && Date.parse(cached.fetched_at) >= latestDue(region, due))
            histories.set(counter, cached.data);
        } else {
          const data = await history(counter);
          if (data.stale) throw new Error("Stale history");
          await db("sma_alert_history?on_conflict=counter", {
            method: "POST",
            prefer: "resolution=merge-duplicates,return=minimal",
            body: { counter, data, fetched_at: new Date(now).toISOString() },
          });
          histories.set(counter, data);
        }
      } catch {
        failed = true;
      }
    }
    for (const original of relevant) {
      // Re-read after retrieval so a newly disabled/archived line cannot send from the old snapshot.
      const current = (
        await db(
          `sma_push_devices?id=eq.${original.id}&enabled=eq.true&select=*`,
        )
      )[0];
      if (!current) continue;
      for (const line of current.lines.filter((l) => l.region === region)) {
        const data = histories.get(line.counter),
          reference = data?.dates?.at(-1);
        if (
          !data ||
          !reference ||
          (!start && reference !== expected) ||
          (start && reference > expected)
        )
          continue;
        const originalLine = original.lines.find(
          (old) =>
            old.counter === line.counter &&
            old.period === line.period &&
            old.target_frequency === line.target_frequency,
        );
        if (!originalLine) continue;
        checked++;
        const kind = evaluateSignal(data, line, current.settings, start);
        if (
          !kind ||
          evaluateSignal(data, originalLine, original.settings, start) !== kind
        )
          continue;
        const session = start
          ? dateInZone(due, "Asia/Singapore").date
          : reference;
        const key = createHash("sha256")
          .update(
            JSON.stringify([
              current.id,
              line.counter,
              line.period,
              line.target_frequency,
              kind,
              session,
            ]),
          )
          .digest("hex");
        if (
          !(await call("sma_claim_event", { p_key: key, p_device: current.id }))
        )
          continue;
        const label = line.custom_name || `SMA (${line.period} days)`,
          title =
            kind === "buy"
              ? "Buy signal"
              : kind === "monitor"
                ? "Impending buy · end of trading"
                : "Impending buy · start of trading";
        const body =
          kind === "monitor_start"
            ? `${line.name} · ${label}: the last adjusted close (${reference}) is above the line. Monitor live prices online.`
            : `${line.name} ${kind === "buy" ? "crossed above" : "closed below"} ${label}. Adjusted close ${reference} · ${data.currency}. Research signal only.`;
        let status = "sent",
          code = null;
        try {
          await send(current, {
            title: `${line.symbol} · ${title}`,
            body,
            tag: key,
            url: "/#alerts",
          });
          posted++;
        } catch (error) {
          code = Number.isInteger(error.statusCode) ? error.statusCode : null;
          status = [404, 410].includes(code) ? "gone" : "failed";
          failed = true;
          if (status === "gone")
            await db(`sma_push_devices?id=eq.${current.id}`, {
              method: "PATCH",
              body: { enabled: false },
            });
        }
        await db("sma_alert_events?key=eq." + key, {
          method: "PATCH",
          body: { status, code },
        });
      }
    }
  } catch {
    failed = true;
  }
  const status = failed ? "failed" : "ok";
  await db(
    `sma_alert_runs?job=eq.${job}&due=eq.${encodeURIComponent(dueISO)}`,
    {
      method: "PATCH",
      body: { status, finished_at: new Date().toISOString(), checked, posted },
    },
  );
  return { status, checked, posted };
}
