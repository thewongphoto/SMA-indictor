import { test } from "node:test";
import webpush from "web-push";
import { createHash } from "node:crypto";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import {
  evaluateSignal,
  latestDue,
  expectedDate,
  runAlerts,
  cleanDevice,
  pushConfig,
  vapidReady,
} from "../lib/push.js";
import { parseHistory, securityFromQuote } from "../lib/market.js";
import { database } from "../lib/supabase.js";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const LINE = {
  counter: "YAHOO:D05.SI",
  symbol: "D05.SI",
  region: "SG",
  period: 2,
  target_frequency: 4,
  custom_name: "",
  name: "DBS",
  alert_buy: true,
  alert_monitor: true,
  alert_start: true,
};
const SETTINGS = {
  phone_buy: true,
  phone_monitor: true,
  phone_monitor_start: true,
};

test("scheduled signal rules match the native Python engine across equality, gaps and type switches", () => {
  const source = `
import json
from sma_analyzer.notifications import evaluate_eod,NotificationSettings
from sma_analyzer.storage import SavedLine
from sma_analyzer.engine import simple_moving_average
from itertools import product
samples=[[4,2,5],[4,2,2,5],[1,1,1],[3,2,1],[1,2,3],[4,None,5,4,3],[4,2,None,5],[4,2,5,None],[4,2,5,5,5,6]]
result=[]
for prices in samples:
 for bits in product([False,True],repeat=6):
  line=SavedLine(1,'DEMO-US','Oscillating',2,4,True,True,False,'',*bits[:3])
  settings=NotificationSettings(phone_buy=bits[3],phone_monitor=bits[4],phone_monitor_start=bits[5])
  events=evaluate_eod(prices,line,settings)
  sma=simple_moving_average(prices,2)
  start='monitor_start' if bits[2] and bits[5] and prices[-1] is not None and sma[-1] is not None and prices[-1]>sma[-1] else None
  result.append(dict(prices=prices,bits=bits,end=events[0].kind if events else None,start=start))
print(json.dumps(result))`;
  const child = spawnSync(process.env.PYTHON || "python3", ["-c", source], {
    cwd: root,
    encoding: "utf8",
  });
  assert.equal(child.status, 0, child.stderr);
  for (const row of JSON.parse(child.stdout)) {
    const [
      alert_buy,
      alert_monitor,
      alert_start,
      phone_buy,
      phone_monitor,
      phone_monitor_start,
    ] = row.bits;
    const line = { ...LINE, alert_buy, alert_monitor, alert_start },
      settings = { phone_buy, phone_monitor, phone_monitor_start };
    assert.equal(
      evaluateSignal({ prices: row.prices }, line, settings),
      row.end,
      JSON.stringify(row),
    );
    assert.equal(
      evaluateSignal({ prices: row.prices }, line, settings, true),
      row.start,
      JSON.stringify(row),
    );
  }
});

test("all four Singapore-time slots and weekday rollbacks match native scheduling", () => {
  const source = `
import json
from datetime import datetime,timezone
from sma_analyzer.schedule import latest_due,expected_session_date,job_details
out=[]
for value in ['2026-11-13T22:30:00+00:00','2026-11-16T01:00:00+00:00','2026-11-15T10:30:00+00:00','2026-11-16T13:30:00+00:00']:
 now=datetime.fromisoformat(value)
 for job in ['US','SG','US_START','SG_START']:
  region,phase=job_details(job);due=latest_due(region,now,phase)
  out.append(dict(now=now.timestamp()*1000,job=job,due=due.timestamp()*1000,expected=expected_session_date(region,due,phase).isoformat()))
print(json.dumps(out))`;
  const child = spawnSync(process.env.PYTHON || "python3", ["-c", source], {
    cwd: root,
    encoding: "utf8",
  });
  assert.equal(child.status, 0, child.stderr);
  for (const row of JSON.parse(child.stdout)) {
    assert.equal(latestDue(row.job, row.now), row.due);
    assert.equal(expectedDate(row.job, row.due), row.expected);
  }
});

function fixture({
  date = "2026-11-12",
  sendFails = false,
  disableDuringFetch = false,
} = {}) {
  const now = Date.parse("2026-11-12T10:30:10Z"),
    claims = new Set(),
    events = new Set(),
    writes = [],
    device = {
      id: "00000000-0000-4000-8000-000000000001",
      created_at: "2026-01-01T00:00:00Z",
      enabled: true,
      settings: SETTINGS,
      lines: [{ ...LINE }],
    };
  let sent = 0,
    fetched = 0;
  const db = async (path, options) => {
    if (options) {
      writes.push({ path, ...options });
      return [];
    }
    if (path.startsWith("sma_push_devices"))
      return device.enabled ? [device] : [];
    return [];
  };
  const call = async (name, body) => {
    const set = name === "sma_claim_run" ? claims : events,
      key = name === "sma_claim_run" ? body.p_job + body.p_due : body.p_key;
    if (set.has(key)) return false;
    set.add(key);
    return true;
  };
  const history = async () => {
    fetched++;
    if (disableDuringFetch) device.enabled = false;
    return {
      prices: [4, 2, 5],
      dates: ["2026-11-10", "2026-11-11", date],
      currency: "SGD",
      stale: false,
    };
  };
  const send = async () => {
    sent++;
    if (sendFails)
      throw Object.assign(new Error("fixture"), { statusCode: 410 });
  };
  return {
    now,
    db,
    call,
    history,
    send,
    writes,
    device,
    counts: () => ({ sent, fetched }),
  };
}
test("concurrent schedules claim once and do not replay a delivered close", async () => {
  const f = fixture();
  const results = await Promise.all([runAlerts("SG", f), runAlerts("SG", f)]);
  assert.equal(results.filter((x) => x.status === "already_checked").length, 1);
  assert.deepEqual(f.counts(), { sent: 1, fetched: 1 });
  assert.equal((await runAlerts("SG", f)).status, "already_checked");
  assert.equal(f.counts().sent, 1);
});
test("old close, removed device and expired scheduled calls do not notify", async () => {
  const old = fixture({ date: "2026-11-11" });
  assert.equal((await runAlerts("SG", old)).posted, 0);
  const removed = fixture({ disableDuringFetch: true });
  assert.equal((await runAlerts("SG", removed)).posted, 0);
  const expired = fixture();
  expired.now += 3600000;
  assert.equal((await runAlerts("SG", expired)).status, "expired");
  assert.equal(expired.counts().fetched, 0);
});
test("expired push subscriptions are disabled and failed sends are recorded", async () => {
  const f = fixture({ sendFails: true }),
    result = await runAlerts("SG", f);
  assert.equal(result.status, "failed");
  assert.equal(result.posted, 0);
  assert.ok(f.writes.some((x) => x.body?.enabled === false));
  assert.ok(
    f.writes.some((x) => x.body?.status === "gone" && x.body?.code === 410),
  );
});
test("Supabase modern secret keys are sent as apikey, never as JWT Bearer tokens", async () => {
  const original = globalThis.fetch,
    oldURL = process.env.SUPABASE_URL,
    oldKey = process.env.SUPABASE_SECRET_KEY;
  process.env.SUPABASE_URL = "https://example.supabase.co";
  process.env.SUPABASE_SECRET_KEY = "sb_secret_fixture";
  try {
    globalThis.fetch = async (url, options) => {
      assert.equal(options.headers.apikey, "sb_secret_fixture");
      assert.equal(options.headers.Authorization, undefined);
      return Response.json([]);
    };
    await database("sma_push_devices?select=id");
  } finally {
    globalThis.fetch = original;
    oldURL === undefined
      ? delete process.env.SUPABASE_URL
      : (process.env.SUPABASE_URL = oldURL);
    oldKey === undefined
      ? delete process.env.SUPABASE_SECRET_KEY
      : (process.env.SUPABASE_SECRET_KEY = oldKey);
  }
});
test("market parser excludes unfinished bars and refuses missing adjusted prices", () => {
  const stamp = Date.parse("2026-11-12T14:30:00Z") / 1000,
    timestamps = Array.from({ length: 5 }, (_, i) => stamp - (4 - i) * 86400),
    meta = {
      symbol: "AAPL",
      exchangeName: "NMS",
      instrumentType: "EQUITY",
      currency: "USD",
      exchangeTimezoneName: "America/New_York",
    };
  const payload = {
    chart: {
      result: [
        {
          meta,
          timestamp: timestamps,
          indicators: {
            quote: [{ close: [1, 2, 3, 4, 5] }],
            adjclose: [{ adjclose: [0.8, 1.8, 2.8, 3.8, 4.8] }],
          },
        },
      ],
    },
  };
  const result = parseHistory(
    payload,
    "AAPL",
    Date.parse("2026-11-12T16:00:00Z"),
  );
  assert.equal(result.prices.length, 4);
  assert.equal(result.prices.at(-1), 3.8);
  payload.chart.result[0].indicators.adjclose[0].adjclose[0] = null;
  assert.throws(() => parseHistory(payload, "AAPL"), /adjusted/i);
  assert.equal(
    securityFromQuote({
      symbol: "EURUSD=X",
      exchange: "CCY",
      quoteType: "CURRENCY",
    }),
    null,
  );
});

test("opening reminders use only a freshly verified closing snapshot and never fetch live prices", async () => {
  const now = Date.parse("2026-11-16T01:00:10Z"),
    due = latestDue("SG_START", now),
    closing = latestDue("SG", due);
  for (const fresh of [true, false]) {
    const device = {
      id: "00000000-0000-4000-8000-000000000001",
      created_at: "2026-01-01T00:00:00Z",
      settings: SETTINGS,
      lines: [{ ...LINE }],
    };
    let sent = 0,
      fetched = 0;
    const data = {
      prices: [1, 2, 3],
      dates: ["2026-11-11", "2026-11-12", "2026-11-13"],
      currency: "SGD",
    };
    const db = async (path, options) => {
      if (options) return [];
      if (path.startsWith("sma_push_devices")) return [device];
      if (path.startsWith("sma_alert_history"))
        return [
          {
            data,
            fetched_at: new Date(closing + (fresh ? 0 : -60000)).toISOString(),
          },
        ];
      return [];
    };
    const result = await runAlerts("SG_START", {
      now,
      db,
      call: async () => true,
      history: async () => {
        fetched++;
        throw new Error("No live fetch allowed");
      },
      send: async (device, payload) => {
        sent++;
        assert.ok(payload.body.includes("last adjusted close"));
      },
    });
    assert.equal(fetched, 0);
    assert.equal(sent, fresh ? 1 : 0);
    assert.equal(result.posted, sent);
  }
});
test("when all signal types are off the closing job makes no history request", async () => {
  const f = fixture();
  f.device.settings = {
    phone_buy: false,
    phone_monitor: false,
    phone_monitor_start: false,
  };
  assert.equal((await runAlerts("SG", f)).posted, 0);
  assert.equal(f.counts().fetched, 0);
});

test("setup is ready only when keys match and Supabase has the matching scheduler secret and origin", async () => {
  const names = [
      "SUPABASE_URL",
      "SUPABASE_SECRET_KEY",
      "VAPID_PUBLIC_KEY",
      "VAPID_PRIVATE_KEY",
      "CRON_SECRET",
    ],
    old = Object.fromEntries(names.map((name) => [name, process.env[name]])),
    fetch = globalThis.fetch;
  const pair = webpush.generateVAPIDKeys(),
    other = webpush.generateVAPIDKeys(),
    secret = "scheduler-fixture-with-at-least-32-characters";
  Object.assign(process.env, {
    SUPABASE_URL: "https://fixture.supabase.co",
    SUPABASE_SECRET_KEY: "sb_secret_fixture",
    VAPID_PUBLIC_KEY: pair.publicKey,
    VAPID_PRIVATE_KEY: pair.privateKey,
    CRON_SECRET: secret,
  });
  try {
    let hash = createHash("sha256").update(secret).digest("hex");
    globalThis.fetch = async () =>
      Response.json({
        schema_ready: true,
        scheduled_jobs: 4,
        app_url: "https://sma.example",
        cron_secret_sha256: hash,
      });
    assert.equal((await pushConfig("https://sma.example")).ready, true);
    assert.equal((await pushConfig("https://wrong.example")).ready, false);
    hash = "mismatch";
    assert.equal((await pushConfig("https://sma.example")).ready, false);
    process.env.VAPID_PRIVATE_KEY = other.privateKey;
    assert.equal(vapidReady(), false);
    const result = JSON.stringify(await pushConfig("https://sma.example"));
    assert.ok(!result.includes(secret));
    assert.ok(!result.includes(other.privateKey));
  } finally {
    globalThis.fetch = fetch;
    for (const [name, value] of Object.entries(old)) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
  }
});
