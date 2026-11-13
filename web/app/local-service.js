"use client";
import { localValue, clearHistories } from "./local-store";
import { calculate, cancelCalculations } from "./python";
import catalog from "../lib/catalog.json";
import packageInfo from "../package.json";
let core,
  initializing,
  mutations = Promise.resolve();
const jobs = new Map();
let activeJob = null;
const defaults = () => ({
  schema: 1,
  lines: [],
  archive: [],
  securities: {},
  allocations: {},
  choices: {},
  nextId: 1,
  settings: { phone_buy: true, phone_monitor: true, phone_monitor_start: true },
  revision: 0,
  events: [],
  push: { enabled: false, pending: false },
});
async function load() {
  if (!core) {
    initializing ||= localValue("library").then(
      (value) => (core = value || defaults()),
    );
    await initializing;
  }
  return core;
}
async function persist() {
  await localValue("library", core);
}
function event(operation, status, detail) {
  core.events.push({ at: new Date().toISOString(), operation, status, detail });
  core.events = core.events.slice(-200);
}
export async function remote(path, body, method) {
  const response = await fetch("/api/" + path, {
    method: method || (body ? "POST" : "GET"),
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  let value;
  try {
    value = await response.json();
  } catch {
    throw new Error(
      "The server did not return a usable response. Downloaded data is retained.",
    );
  }
  if (!response.ok) {
    const error = new Error(value.error || "Request failed");
    error.status = response.status;
    throw error;
  }
  return value;
}
function integer(value, name, min = 1, max = Number.MAX_SAFE_INTEGER) {
  if (!Number.isSafeInteger(value) || value < min || value > max)
    throw new Error(
      `${name} must be a whole number between ${min} and ${max}.`,
    );
  return value;
}
function name(value) {
  if (
    typeof value !== "string" ||
    value.length > 60 ||
    /[\u0000-\u001f\u007f]/.test(value)
  )
    throw new Error(
      "Use a name up to 60 characters, without control characters.",
    );
  return value.trim();
}
function colorHex(index) {
  if (index < 0)
    return catalog.colors[-index - 1]?.color || catalog.automatic[0];
  if (index < catalog.automatic.length) return catalog.automatic[index];
  const h = (index * 0.61803398875 + 0.13) % 1,
    s = 0.52,
    v = 0.98,
    i = Math.floor(h * 6),
    f = h * 6 - i,
    p = v * (1 - s),
    q = v * (1 - f * s),
    t = v * (1 - (1 - f) * s);
  const rgb = [
    [v, t, p],
    [q, v, p],
    [p, v, t],
    [p, q, v],
    [t, p, v],
    [v, p, q],
  ][i % 6];
  return (
    "#" +
    rgb
      .map((x) =>
        Math.round(x * 255)
          .toString(16)
          .padStart(2, "0"),
      )
      .join("")
  );
}
function allocationKey(line) {
  return `${line.counter}|${line.scenario}|${line.period}`;
}
function renderLine(line) {
  const color = core.allocations[allocationKey(line)] ?? 0;
  return {
    ...line,
    name: line.custom_name || `SMA (${line.period} days)`,
    color,
    color_hex: colorHex(color),
  };
}
function stateFor(prices, period) {
  if (prices.length < period || !prices.slice(-period).every(Number.isFinite))
    return "Unknown";
  let sum = 0,
    run = 0;
  for (let i = 0; i < prices.length; i++) {
    const value = prices[i];
    if (!Number.isFinite(value)) {
      sum = 0;
      run = 0;
      continue;
    }
    sum += value;
    run++;
    if (run > period) sum -= prices[i - period];
  }
  const average = sum / period,
    price = prices.at(-1);
  return price > average ? "Above" : price < average ? "Below" : "On line";
}
async function state() {
  await load();
  const cards = [];
  for (const counter of new Set(core.lines.map((line) => line.counter))) {
    const lines = core.lines
        .filter((line) => line.counter === counter)
        .map(renderLine),
      data = await localValue("history:" + counter),
      prices = data?.prices || [],
      last = prices.at(-1),
      previous = prices.at(-2),
      states = Object.fromEntries(
        lines.map((line) => [line.id, stateFor(prices, line.period)]),
      );
    cards.push({
      counter,
      security: core.securities[counter],
      lines,
      states,
      below: Object.values(states).filter((x) => x === "Below").length,
      price: Number.isFinite(last) ? last : null,
      change:
        Number.isFinite(last) && Number.isFinite(previous) && previous !== 0
          ? (last / previous - 1) * 100
          : null,
      currency: data?.currency || core.securities[counter]?.currency || "",
      date: data?.dates?.at(-1) || "",
      stale: !data || Date.now() / 1000 - data.fetched_at > 86400,
    });
  }
  cards.sort(
    (a, b) =>
      Boolean(b.below) - Boolean(a.below) ||
      a.security.name.localeCompare(b.security.name),
  );
  return {
    cards,
    archive: core.archive.map(renderLine),
    colors: catalog.colors,
    settings: core.settings,
    version: packageInfo.version,
    preview: false,
    storage: "local",
    push: { ...core.push },
  };
}
function allocate(line) {
  const key = allocationKey(line);
  if (!(key in core.allocations)) {
    const prefix = `${line.counter}|${line.scenario}|`,
      indexes = Object.entries(core.allocations)
        .filter(([k]) => k.startsWith(prefix))
        .map(([, v]) => v)
        .filter((v) => v >= 0);
    core.allocations[key] = indexes.length ? Math.max(...indexes) + 1 : 0;
  }
}
async function history(key, cached = false) {
  const saved = await localValue("history:" + key);
  if (cached || !navigator.onLine) {
    if (!saved)
      throw new Error(
        "Download this chart while online before opening it offline.",
      );
    return saved;
  }
  // Opening already-downloaded prices does not make another request within 6 hours.
  if (saved && Date.now() / 1000 - saved.fetched_at < 21600) return saved;
  try {
    const data = await remote("market/history", { key });
    core.securities[key] = data.security;
    await localValue("history:" + key, data);
    event("history", "ok", "Downloaded completed adjusted daily closes.");
    await persist();
    return data;
  } catch (error) {
    event(
      "history",
      "failed",
      "Market request failed; prior downloads retained.",
    );
    await persist();
    if (saved) return { ...saved, stale: true };
    throw error;
  }
}
async function chart(body) {
  const data = await history(body.key, Boolean(body.cached)),
    lines = core.lines.filter((x) => x.counter === body.key).map(renderLine);
  if (!body.period && !lines.length)
    return { ...data, lines: [], result: null, backtest: null };
  return calculate({
    data,
    lines,
    period: body.period,
    target: body.target || 4,
    horizon: body.horizon || "Max",
    years: body.years || "3",
  });
}
function lineById(id) {
  const line = core.lines.find((x) => x.id === id);
  if (!line) throw new Error("This SMA is no longer saved.");
  return line;
}
async function revision() {
  core.revision = Math.max(Date.now(), core.revision + 1);
  if (core.push.enabled) core.push.pending = true;
  await persist();
  window.dispatchEvent(new Event("sma-push-sync"));
}
export function localApi(path, body = {}, method) {
  // Serialize writes to prevent rapid switches or duplicate Save clicks losing data.
  const run = () => handle(path, body, method);
  if (
    ["save", "line", "restore", "settings", "clear-cache", "import"].includes(
      path,
    )
  ) {
    const write = async () => {
      await load();
      const before = structuredClone(core);
      try {
        return await run();
      } catch (error) {
        core = before;
        throw error;
      }
    };
    const result = mutations.then(write);
    mutations = result.catch(() => {});
    return result;
  }
  return run();
}
async function handle(path, body = {}, method) {
  await load();
  if (path === "state") return state();
  if (path === "search") {
    const result = await remote("market/search", { query: body.query });
    for (const security of result.results)
      core.securities[security.key] = security;
    event("search", "ok", "Submitted security lookup.");
    await persist();
    return result;
  }
  if (path === "chart") return chart(body);
  if (path === "optimize") {
    const target = integer(body.target, "Frequency");
    const data = await history(body.key, true);
    for (const old of jobs.values())
      if (old.status === "running") old.status = "cancelled";
    if (activeJob) cancelCalculations();
    for (const key of [...jobs.keys()].slice(0, -4)) jobs.delete(key);
    const id = crypto.randomUUID(),
      job = { status: "running" };
    jobs.set(id, job);
    activeJob = id;
    const task = async () => {
      try {
        const fingerprint = await crypto.subtle.digest(
          "SHA-256",
          new TextEncoder().encode(JSON.stringify([data.prices, data.dates])),
        );
        const hash = Array.from(new Uint8Array(fingerprint), (x) =>
          x.toString(16).padStart(2, "0"),
        ).join("");
        const key = `${packageInfo.version}|${body.key}|${target}|${hash}`;
        if (job.status !== "running" || activeJob !== id) return;
        const saved = core.lines
            .filter(
              (x) => x.counter === body.key && x.target_frequency === target,
            )
            .at(-1),
          period = saved?.period || core.choices[key];
        const result = await calculate({
          data,
          lines: core.lines
            .filter((x) => x.counter === body.key)
            .map(renderLine),
          target,
          period,
          optimize: true,
        });
        if (job.status !== "running") return;
        core.choices[key] = result.result.period;
        const choices = Object.keys(core.choices);
        for (const old of choices.slice(0, Math.max(0, choices.length - 100)))
          delete core.choices[old];
        await persist();
        job.status = "complete";
        job.data = result;
        if (activeJob === id) activeJob = null;
      } catch (error) {
        if (job.status === "running") {
          job.status = "failed";
          job.error = error.message;
        }
      }
    };
    void task();
    return { job: id };
  }
  if (path.startsWith("jobs/")) {
    const job = jobs.get(path.split("/").at(-1));
    if (!job) throw new Error("Calculation expired. Please run it again.");
    if (method === "DELETE" && job.status === "running") {
      job.status = "cancelled";
      if (activeJob === path.split("/").at(-1)) {
        activeJob = null;
        cancelCalculations();
      }
    }
    return { ...job };
  }
  if (path === "save") {
    const data = await history(body.key, true);
    integer(body.period, "SMA period", 2, data.prices.length);
    integer(body.target, "Frequency");
    if (
      !core.lines.some(
        (x) =>
          x.counter === body.key &&
          x.period === body.period &&
          x.target_frequency === body.target,
      )
    ) {
      const old = core.archive.find(
        (x) =>
          x.counter === body.key &&
          x.period === body.period &&
          x.target_frequency === body.target,
      );
      const line = old || {
        id: core.nextId++,
        counter: body.key,
        scenario: data.scenario,
        period: body.period,
        target_frequency: body.target,
        visible: true,
        push_enabled: true,
        email_enabled: false,
        custom_name: "",
        alert_buy: true,
        alert_monitor: true,
        alert_start: true,
      };
      core.lines.push(line);
      core.archive = core.archive.filter((x) => x.id !== line.id);
      allocate(line);
    }
  } else if (path === "line") {
    const line = lineById(body.id);
    if ("name" in body) line.custom_name = name(body.name);
    if ("color" in body)
      core.allocations[allocationKey(line)] =
        -integer(body.color, "Colour", 0, 11) - 1;
    for (const key of [
      "visible",
      "push_enabled",
      "alert_buy",
      "alert_monitor",
      "alert_start",
    ])
      if (key in body) {
        if (typeof body[key] !== "boolean")
          throw new Error("Invalid switch value");
        line[key] = body[key];
      }
    if (body.archive) {
      core.lines = core.lines.filter((x) => x.id !== line.id);
      core.archive = [
        line,
        ...core.archive.filter((x) => x.id !== line.id),
      ].slice(0, 10);
    }
  } else if (path === "restore") {
    const line = core.archive.find((x) => x.id === body.id);
    if (!line) throw new Error("Archived line is no longer available.");
    if (
      !core.lines.some(
        (x) =>
          x.counter === line.counter &&
          x.period === line.period &&
          x.target_frequency === line.target_frequency,
      )
    )
      core.lines.push(line);
    core.archive = core.archive.filter((x) => x.id !== line.id);
  } else if (path === "settings") {
    for (const key of ["phone_buy", "phone_monitor", "phone_monitor_start"])
      if (key in body) {
        if (typeof body[key] !== "boolean")
          throw new Error("Invalid switch value");
        core.settings[key] = body[key];
      }
  } else if (path === "clear-cache") {
    await clearHistories();
    core.choices = {};
  } else if (path === "log") return { events: core.events };
  else if (path === "export")
    return {
      version: 1,
      storage: "local",
      cards: (await state()).cards.map(({ security, lines }) => ({
        security,
        lines,
      })),
      settings: core.settings,
    };
  else if (path === "import") return importBackup(body);
  else throw new Error("Unknown local operation");
  await revision();
  return state();
}
async function importBackup(backup) {
  if (
    backup.version !== 1 ||
    !Array.isArray(backup.cards) ||
    backup.cards.length > 100
  )
    throw new Error("Choose a valid SMA saved-parameters backup.");
  const entries = [];
  for (const card of backup.cards) {
    const security = card.security;
    if (
      !security ||
      typeof security.key !== "string" ||
      !/^YAHOO:[A-Z0-9][A-Z0-9.^=-]{0,29}$/.test(security.key) ||
      !["US", "SG"].includes(security.region) ||
      typeof security.name !== "string" ||
      security.name.length > 200 ||
      !Array.isArray(card.lines)
    )
      throw new Error("The backup contains an unsupported security.");
    for (const source of card.lines) {
      if (entries.length >= 500)
        throw new Error("Import up to 500 saved lines at a time.");
      const period = integer(source.period, "SMA period", 2, 100000),
        target = integer(source.target_frequency, "Frequency"),
        custom_name = name(source.custom_name || "");
      const switches = {};
      for (const key of [
        "visible",
        "push_enabled",
        "alert_buy",
        "alert_monitor",
        "alert_start",
      ]) {
        if (source[key] !== undefined && typeof source[key] !== "boolean")
          throw new Error("Invalid backup switch value");
        switches[key] = source[key] ?? true;
      }
      const color = Number.isSafeInteger(source.color) ? source.color : 0;
      if (color < -12 || color > 100000)
        throw new Error("Invalid backup colour");
      entries.push({
        security,
        source: {
          counter: security.key,
          scenario: "Yahoo EOD",
          period,
          target_frequency: target,
          custom_name,
          ...switches,
          email_enabled: false,
        },
        color,
      });
    }
  }
  // Validate every record before replacing any local data. Existing identities win.
  for (const { security, source, color } of entries) {
    if (
      core.lines.some(
        (x) =>
          x.counter === source.counter &&
          x.period === source.period &&
          x.target_frequency === source.target_frequency,
      )
    )
      continue;
    core.securities[security.key] = {
      ...security,
      logo_url: security.logo_url?.startsWith("/logos/")
        ? security.logo_url
        : "",
    };
    const line = { ...source, id: core.nextId++ };
    core.lines.push(line);
    core.archive = core.archive.filter(
      (old) =>
        old.counter !== line.counter ||
        old.period !== line.period ||
        old.target_frequency !== line.target_frequency,
    );
    core.allocations[allocationKey(line)] = color;
  }
  for (const key of ["phone_buy", "phone_monitor", "phone_monitor_start"])
    if (typeof backup.settings?.[key] === "boolean")
      core.settings[key] = backup.settings[key];
  await revision();
  return state();
}
export async function pushData() {
  await load();
  return { core, persist, state };
}
