"use client";
import { useEffect, useRef, useState } from "react";
import Chart from "./chart";
import Signup from "./signup";
import Dialog from "./dialog";
import { localApi, remote } from "./local-service";
import PushControls from "./push-controls";
import { syncPush } from "./push-client";
import { stored } from "./cache";
import CompanyLogo from "./company-logo";
import TargetPreference from "./target-preference";
import HistoryPicker from "./history-picker";
import {historyOf,historyKey,sameHistory,historyLabel} from "../lib/history-window";
import packageInfo from "../package.json";

const labels = {
  library: "Home",
  results: "Charts",
  alerts: "Alerts",
  settings: "Settings",
  search: "Find a security",
  archive: "Archived lines",
  log: "Request log",
};
const defaultState = {
  cards: [],
  archive: [],
  colors: [],
  settings: {},
  version: packageInfo.version,
};
const money = (value) =>
  Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
function Logo({ security }) {
  return <CompanyLogo security={security} />;
}
function MotionLogo() {
  return (
    <div className="motion-logo">
      <img src="/app-icon.png" alt="Crosspoints" />
    </div>
  );
}
// Per-line signal type field, its master setting key, and the shared app title.
const LINE_SIGNAL_TYPES = [
  ["alert_buy", "phone_buy", "Buy signal"],
  ["alert_monitor", "phone_monitor", "Impending buy signal (End of trading)"],
  [
    "alert_start",
    "phone_monitor_start",
    "Impending buy signal (Start of trading)",
  ],
];

function Toggle({ checked, onChange, label, disabled = false }) {
  return (
    <button
      className="toggle"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
    >
      <span />
    </button>
  );
}

export default function App() {
  const [welcome, setWelcome] = useState(false),
    [guide, setGuide] = useState(false);
  const guideReturn = useRef(null);
  const [tab, setTab] = useState("library"),
    [state, setState] = useState(defaultState),
    [ready, setReady] = useState(false),
    [loading, setLoading] = useState(true);
  const [error, setError] = useState(""),
    [offline, setOffline] = useState(false),
    [expanded, setExpanded] = useState({}),
    [query, setQuery] = useState(""),
    [submitted, setSubmitted] = useState(""),
    [matches, setMatches] = useState([]),
    [searching, setSearching] = useState(false);
  const [chart, setChart] = useState(null),
    [builder, setBuilder] = useState(null),
    [priceHistory,setPriceHistory]=useState(historyOf()),
    [historyPicker,setHistoryPicker]=useState(false),
    [editingLine,setEditingLine]=useState(null),
    [saveChoice,setSaveChoice]=useState(false),
    [target, setTarget] = useState(12),
    [custom, setCustom] = useState(false),
    [job, setJob] = useState(null),
    [jobSecurity, setJobSecurity] = useState(""),
    [edit, setEdit] = useState(null),
    [horizon, setHorizon] = useState("Max"),
    [years, setYears] = useState(3),
    [theme, setTheme] = useState("system"),
    [events, setEvents] = useState([]),
    [keyboard, setKeyboard] = useState(false),
    [standalone, setStandalone] = useState(false);
  const generation = useRef(0),
    jobRef = useRef(null),
    securitySearch = useRef(null);
  const backend = useRef("local");
  async function api(path, body, method) {
    if (path === "state") {
      if (navigator.onLine) {
        backend.current = (await remote("session")).storage;
        localStorage.setItem("sma-storage-mode", backend.current);
      } else {
        backend.current = localStorage.getItem("sma-storage-mode") || "local";
      }
    }
    if (backend.current === "local")
      return await localApi(path, body, method);
    const value = await remote(path, body, method);
    return Array.isArray(value.cards)
      ? { ...value, storage: "worker" }
      : value;
  }
  async function refresh() {
    const value = await api("state");
    setState(value);
    setReady(true);
    await stored("state", value);
    return value;
  }
  useEffect(() => {
    setWelcome(
      !localStorage.getItem("sma-welcome-done") ||
        new URLSearchParams(location.search).get("welcome") === "1",
    );
    setTheme(localStorage.getItem("sma-theme") || "system");
    setStandalone(
      matchMedia("(display-mode: standalone)").matches ||
        Boolean(navigator.standalone),
    );
    const connection = () => setOffline(!navigator.onLine),
      back = (event) => {
        cancel();
        setLoading(false);
        setEdit(null);
        setHistoryPicker(false);setSaveChoice(false);
        setGuide(false);
        setTab(event.state?.tab || "library");
        setError("");
      };
    const resize = () => {
      document.documentElement.style.setProperty(
        "--app-height",
        `${window.visualViewport?.height || window.innerHeight}px`,
      );
      const focused = document.activeElement;
      if (focused?.matches("input,textarea"))
        focused.scrollIntoView({ block: "nearest" });
    };
    resize();
    window.visualViewport?.addEventListener("resize", resize);
    const openAlerts = (event) => {
      if (event.data?.type === "open-alerts") {
        cancel();
        setTab("alerts");
      }
    };
    navigator.serviceWorker?.addEventListener("message", openAlerts);
    if (location.hash === "#alerts") setTab("alerts");
    const updatePush = () => {
      if (backend.current === "local")
        localApi("state")
          .then(setState)
          .catch(() => {});
    };
    const synchronize = () => syncPush().catch(() => {});
    window.addEventListener("sma-push-updated", updatePush);
    window.addEventListener("sma-push-sync", synchronize);
    window.addEventListener("online", synchronize);
    connection();
    window.addEventListener("online", connection);
    window.addEventListener("offline", connection);
    window.addEventListener("popstate", back);
    stored("state")
      .then((value) => {
        if (value) {
          setState(value);
          if (!navigator.onLine) setReady(true);
        }
      })
      .catch(() => {});
    refresh()
      .catch((error) => {
        if (navigator.onLine) setError(error.message);
      })
      .finally(() => {
        setLoading(false);
        if (backend.current === "local") syncPush().catch(() => {});
      });
    if ("serviceWorker" in navigator)
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    return () => {
      navigator.serviceWorker?.removeEventListener("message", openAlerts);
      window.removeEventListener("sma-push-updated", updatePush);
      window.removeEventListener("sma-push-sync", synchronize);
      window.removeEventListener("online", synchronize);
      window.removeEventListener("online", connection);
      window.removeEventListener("offline", connection);
      window.removeEventListener("popstate", back);
      window.visualViewport?.removeEventListener("resize", resize);
    };
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("sma-theme", theme);
  }, [theme]);
  function navigate(next) {
    if (guide) {
      setChart(guideReturn.current);
      setGuide(false);
    }
    cancel();
    setLoading(false);
    setEdit(null);
    if (next === "search") {
      setBuilder(null);
      setQuery("");
      setSubmitted("");
      setMatches([]);
    }
    setTab(next);
    setError("");
    history.pushState({ tab: next }, "", `#${next}`);
  }
  function fail(error) {
    setError(error.message || String(error));
  }
  async function openChart(security, line = null, cached = false, destination = "results") {
    const token = ++generation.current;
    setError("");
    setLoading(true);
    const cacheKey = `chart:${security.key}:${line?.period || 0}:${line?.target_frequency || 4}${historyKey(line)}`;
    try {
      const value =
        offline || cached
          ? await stored(cacheKey)
          : await api("chart", {
              key: security.key,
              period: line?.period,
              ...historyOf(line),
              target: line?.target_frequency,
            });
      if (!value)
        throw new Error(
          "Download this chart while online before opening it offline.",
        );
      if (token !== generation.current) return;
      setPriceHistory(historyOf(line || value.result));
      setEditingLine(line || null);
      if (destination === "search") {
        setBuilder(value);
        setChart(value);
        setQuery(value.security.ticker);
        setSubmitted("");
        setMatches([]);
      } else {
        setBuilder(null);
        setChart(value);
        const nextTarget = line?.target_frequency || 4;
        setTarget(nextTarget);
        setCustom(![4, 6, 12].includes(nextTarget));
        setHorizon("Max");
        setTab("results");
        history.pushState({ tab: "results" }, "", "#results");
      }
      await stored(cacheKey, value);
    } catch (e) {
      if (token === generation.current) fail(e);
    } finally {
      if (token === generation.current) setLoading(false);
    }
  }
  async function search(event) {
    event.preventDefault();
    const text = query.trim();
    if (!text || searching) return;
    const token = ++generation.current;
    setBuilder(null);
    setSearching(true);
    setError("");
    try {
      const result = await api("search", { query: text });
      if (token === generation.current) {
        setMatches(result.results);
        setSubmitted(text);
      }
    } catch (e) {
      if (token === generation.current) fail(e);
    } finally {
      setSearching(false);
    }
  }
  async function openGuide() {
    guideReturn.current = chart;
    setGuide(true);
    setError("");
    try {
      const result = await api("search", {
        query: state.preview ? "AAPL" : "VOO",
      });
      const security = result.results.find(
        (item) => item.ticker === (state.preview ? "AAPL" : "VOO"),
      );
      if (!security) throw new Error("The example is currently unavailable");
      await openChart(security);
      setTarget(4);
    } catch (e) {
      setGuide(false);
      fail(e);
    }
  }
  async function optimize(source = chart) {
    if (!source) return;
    const token = ++generation.current;
    const frequency = Number(target);
    if (!Number.isSafeInteger(frequency) || frequency < 1) {
      setError("Enter a positive whole-number frequency.");
      return;
    }
    setError("");
    setJobSecurity(source.security.ticker);
    setJob("pending");
    try {
      const result = await api("optimize", {
        key: source.security.key,
        target: frequency,
        ...priceHistory,
      });
      if (token !== generation.current) {
        await api("jobs/" + result.job, null, "DELETE");
        return;
      }
      jobRef.current = result.job;
      setJob(result.job);
      while (token === generation.current) {
        await new Promise((resolve) => setTimeout(resolve, 600));
        const next = await api("jobs/" + result.job);
        if (token !== generation.current) return;
        if (next.status === "complete") {
          setChart(next.data);
          setHorizon("Max");
          if (tab === "search") {
            setTab("results");
            history.pushState({ tab: "results" }, "", "#results");
          }
          await stored(
            `chart:${source.security.key}:${next.data.result.period}:${frequency}${historyKey(next.data.result)}`,
            next.data,
          );
          break;
        }
        if (next.status === "failed" || next.status === "cancelled")
          throw new Error(next.error || "Calculation cancelled");
      }
    } catch (e) {
      if (token === generation.current) fail(e);
    } finally {
      if (token === generation.current) {
        setJob(null);
        jobRef.current = null;
      }
    }
  }
  async function cancel() {
    generation.current++;
    const current = jobRef.current;
    setJob(null);
    jobRef.current = null;
    if (current) await api("jobs/" + current, null, "DELETE").catch(fail);
  }
  async function mutate(path, body) {
    try {
      const value = await api(path, body);
      if(path==='line' && body.archive && editingLine?.id===body.id)setEditingLine(null);
      setState(value);
      await stored("state", value);
      return value;
    } catch (e) {
      fail(e);
      return null;
    }
  }
  async function changeLine(line, patch) {
    const token = generation.current;
    const value = await mutate("line", { id: line.id, ...patch });
    if (value && chart) {
      const next = await api("chart", {
        key: chart.security.key,
        period: chart.result?.period,
        target: chart.result?.target,
        ...historyOf(chart.result),
        horizon,
        years,
        cached: true,
      });
      if (token === generation.current) setChart(next);
      await stored(
        `chart:${next.security.key}:${next.result?.period || 0}:${next.result?.target || 4}${historyKey(next.result)}`,
        next,
      );
    }
    return value;
  }
  async function backtest(value, newYears = years) {
    const token = ++generation.current;
    setHorizon(value);
    try {
      const next = await api("chart", {
        key: chart.security.key,
        period: chart.result.period,
        target: chart.result.target,
        ...historyOf(chart.result),
        horizon: value,
        years: newYears,
        cached: true,
      });
      if (token === generation.current) setChart(next);
    } catch (e) {
      if (token === generation.current) fail(e);
    }
  }
  async function save(mode) {
    if (!chart?.result || !sameHistory(priceHistory,chart.result)) return;
    if(editingLine && !mode && !(chart.lines||[]).some(line=>line.period===chart.result.period && line.target_frequency===chart.result.target && sameHistory(line,chart.result))) {setSaveChoice(true);return;}
    const token=generation.current;
    const value=await mutate("save",{key:chart.security.key,period:chart.result.period,target:chart.result.target,...historyOf(chart.result),
      ...(mode==='update'?{update_id:editingLine.id}:{}),as_new:mode==='new'});
    if(!value)return;
    setSaveChoice(false);setEditingLine(null);
    const next=await api("chart",{key:chart.security.key,period:chart.result.period,target:chart.result.target,...historyOf(chart.result),cached:true});
    if(token===generation.current)setChart(next);
    await stored(`chart:${next.security.key}:${next.result.period}:${next.result.target}${historyKey(next.result)}`,next);
  }
  const selected = chart?.lines.find(
    (line) =>
      line.period === chart.result?.period &&
      line.target_frequency === chart.result?.target && sameHistory(line,chart.result),
  );
  const historyStale=Boolean(chart?.result && !sameHistory(priceHistory,chart.result));
  const below = state.cards.reduce((sum, card) => sum + card.below, 0);
  if (welcome)
    return (
      <Signup
        variant="welcome"
        onDone={() => {
          localStorage.setItem("sma-welcome-done", "1");
          const url = new URL(location.href);
          url.searchParams.delete("welcome");
          history.replaceState(history.state, "", url.pathname + url.search + url.hash);
          setWelcome(false);
        }}
        onUnavailable={() => setWelcome(false)}
      />
    );
  if (!ready && loading)
    return (
      <main className="login">
        <MotionLogo />
        <h1>Opening Crosspoints…</h1>
      </main>
    );
  return (
    <main
      className="app"
      onFocusCapture={(event) => {
        if (["INPUT", "TEXTAREA"].includes(event.target.tagName))
          setKeyboard(true);
      }}
      onBlurCapture={() => setKeyboard(false)}
    >
      <header className={tab === "results" ? "detail-header" : tab === "search" && builder ? "builder-header" : undefined}>
        {!["library", "alerts", "settings"].includes(tab) && (
          <button className="text" onClick={() => tab === "results" && builder ? history.back() : navigate("library")}>
            ‹ Back
          </button>
        )}
        <h1>
          {tab === "search" && builder ? "Set your preference" : tab === "results" && chart ? `${chart.security.ticker}${chart.result ? ` · ${selected?.name || `SMA (${chart.result.period} days)`}` : ""}` : labels[tab]}
        </h1>
        {tab === "library" ? (
          <button className="outline" onClick={() => navigate("search")}>
            + Find SMA
          </button>
        ) : tab === "results" && chart?.result && !guide ? (
          <button className="text" onClick={() => save()} disabled={Boolean(selected)||historyStale}>
            {selected ? "Saved" : "Save"}
          </button>
        ) : null}
      </header>
      <div className="content">
        {state.preview && (
          <p className="notice">
            Preview data · simulated prices for UI testing
          </p>
        )}
        {offline && (
          <div className="notice">
            <strong>You are offline</strong>
            <p>
              Showing downloaded data. Search and new calculations need a
              connection.
            </p>
          </div>
        )}
        {error && (
          <div className="error" role="alert">
            <strong>{error}</strong>
            <button
              onClick={() => {
                setError("");
                if (tab === "search") search({ preventDefault() {} });
                else refresh().catch(fail);
              }}
            >
              Try again
            </button>
          </div>
        )}
        {tab === "library" && (
          <>
            {!standalone && (
              <div className="card install">
                <span>Add to Home Screen for a full-screen view.</span>
                <button
                  className="text"
                  onClick={() =>
                    alert(
                      "In Safari, tap Share, then Add to Home Screen. Enable alerts from the Alerts tab after adding the app to your Home Screen.",
                    )
                  }
                >
                  How
                </button>
              </div>
            )}
            {state.cards.length > 0 ? (
              <>
                <section className="card">
                  <p className="overline">Saved SMAs</p>
                  <h2>
                    {below
                      ? `${below} ${below === 1 ? "line needs" : "lines need"} attention`
                      : "All saved lines at a glance"}
                  </h2>
                  <p>Based on the latest downloaded adjusted closes.</p>
                </section>
                <div className="section-heading">
                  <h3>WATCHLIST</h3>
                  <button className="text" onClick={() => navigate("archive")}>
                    Archive
                  </button>
                </div>
                {state.cards.map((card) => (
                  <section key={card.counter} className="card watch-card">
                    <button
                      className="card-heading"
                      onClick={() =>
                        setExpanded({
                          ...expanded,
                          [card.counter]: !expanded[card.counter],
                        })
                      }
                      aria-expanded={Boolean(expanded[card.counter])}
                    >
                      <Logo security={card.security} />
                      <span className="identity">
                        <strong>{card.security.name}</strong>
                        <small>
                          {card.security.ticker} ·{" "}
                          {card.security.region || card.security.exchange}
                        </small>
                      </span>
                      <span className="quote">
                        <strong>
                          {card.price === null ? "—" : `$${money(card.price)}`}
                        </strong>
                        <small
                          className={card.change < 0 ? "negative" : "positive"}
                        >
                          {card.change == null
                            ? ""
                            : `${card.change < 0 ? "▼" : "▲"} ${Math.abs(card.change).toFixed(1)}%`}
                        </small>
                      </span>
                    </button>
                    <button
                      className="card-summary"
                      onClick={() =>
                        setExpanded({
                          ...expanded,
                          [card.counter]: !expanded[card.counter],
                        })
                      }
                    >
                      <span className={"badge " + (card.below ? "below" : "")}>
                        {card.below
                          ? `${card.below} OF ${card.lines.length} LINES BELOW`
                          : Object.values(card.states).every(
                                (x) => x === "Above",
                              )
                            ? "ABOVE ALL LINES"
                            : "VIEW LINE STATUS"}
                      </span>
                      <span>
                        {expanded[card.counter]
                          ? "Hide lines ▴"
                          : `${card.lines.length} saved lines ▾`}
                      </span>
                    </button>
                    {expanded[card.counter] &&
                      card.lines.map((line) => (
                        <button
                          className="saved-row"
                          key={line.id}
                          onClick={() => openChart(card.security, line)}
                        >
                          <span>
                            <strong>{line.history_start && !line.custom_name ? `SMA (${line.period} days)` : line.name}</strong>
                            <small>
                              {line.history_start && <span className="history-tag">{historyLabel(line,true)}</span>}{line.target_frequency} signals / year · Alert{" "}
                              {line.push_enabled ? "on" : "off"}
                            </small>
                          </span>
                          <span
                            className={
                              "badge " +
                              (card.states[line.id] === "Below" ? "below" : "")
                            }
                          >
                            {card.states[line.id]?.toUpperCase()}
                          </span>
                        </button>
                      ))}
                  </section>
                ))}
              </>
            ) : (
              <section className="empty">
                <h2>No saved SMA lines yet</h2>
                <p>
                  Find a stock or ETF, choose how often you want upward crossing
                  signals, and save the line.
                </p>
                <button className="primary" onClick={() => navigate("search")}>
                  Find a security
                </button>
                <button className="text" onClick={openGuide}>
                  Try the guided example
                </button>
              </section>
            )}
          </>
        )}
        {tab === "search" && (
          <>
            <form className="search" onSubmit={search}>
              <input
                type="search"
                ref={securitySearch}
                enterKeyHint="search"
                placeholder="Company name or ticker"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <button className="primary" disabled={searching || offline}>
                {searching ? "Searching…" : "Search"}
              </button>
            </form>
            <p>
              {builder ? `Selected ${builder.security.ticker} · ${builder.preview ? "Example" : "Daily"} history ready. Search again to choose another security.` : "US and Singapore listed stocks and ETFs. Press Search or Enter to look up matches."}
            </p>
            {submitted && (
              <p>
                {matches.length} matches for “{submitted}”
              </p>
            )}
            {matches.map((security) => (
              <button
                className="search-result"
                key={security.key}
                onClick={() =>
                  openChart(security, null, false, "search")
                }
              >
                <Logo security={security} />
                <span className="identity">
                  <strong>{security.name}</strong>
                  <small>
                    {security.ticker} · {security.region || security.exchange}
                  </small>
                </span>
                <span className="accent">
                  {state.cards.some((card) => card.counter === security.key)
                    ? "Select ›"
                    : "Analyse ›"}
                </span>
              </button>
            ))}
            {submitted && query !== submitted && (
              <p>Press Search to update these results.</p>
            )}
            {submitted && !matches.length && (
              <p>No matches. Try a company name or ticker.</p>
            )}
            {!submitted && !builder && (
              <>
                <h3>RECENT SAVED SECURITIES</h3>
                {state.cards.map((card) => (
                  <button
                    className="search-result"
                    key={card.counter}
                    onClick={() =>
                      openChart(card.security, null, true, "search")
                    }
                  >
                    <Logo security={card.security} />
                    <span>{card.security.name}</span>
                  </button>
                ))}
                <p className="small">
                  Recent selections use downloaded data without a new lookup.
                </p>
              </>
            )}
            {builder && <TargetPreference data={builder} history={priceHistory} onHistory={()=>setHistoryPicker(true)} stale={historyStale} security={builder.security} target={target} custom={custom}
              onSecurity={() => securitySearch.current?.focus()}
              onTarget={(value, isCustom = false) => { setTarget(value); setCustom(isCustom); }}
              onCustom={() => setCustom(true)} onOptimize={() => optimize(builder)}
              disabled={offline || Boolean(job)} calendar={!builder.preview} />}
          </>
        )}
        {tab === "results" &&
          (chart ? (
            <>
              {guide && (
                <section className="card">
                  <h2>Guided example</h2>
                  <p>
                    An SMA smooths closing prices. A crossing from below to
                    above the line can suggest recovery, but prices can fall
                    again.
                  </p>
                  <p>
                    Start with 4 signals a year, then compare equal-budget
                    purchases in Backtest. This matches signal frequency, not
                    profit.
                  </p>
                  <button className="text" onClick={() => navigate("library")}>
                    Finish example
                  </button>
                </section>
              )}
              {historyStale && <section className="notice" role="status"><strong>The period has changed</strong><p>The line below uses {historyLabel(chart.result)||'all available history'}. Recalculate to match {historyLabel(priceHistory)||'all available history'}.</p><p>Showing the earlier result. Nothing is recalculated until you press the button.</p></section>}
              <div className={historyStale?'history-stale':undefined}><Chart chart={chart} colors={state.colors} /></div>
              <TargetPreference data={chart} history={priceHistory} onHistory={()=>setHistoryPicker(true)} stale={historyStale} target={target} custom={custom}
                onTarget={(value, isCustom = false) => { setTarget(value); setCustom(isCustom); }}
                onCustom={() => {
                  setCustom(true); setBuilder(chart); setTab("search");
                  setQuery(chart.security.ticker); setSubmitted(""); setMatches([]);
                  history.pushState({ tab: "search" }, "", "#search");
                }}
                onOptimize={() => optimize(chart)} disabled={offline || Boolean(job)} />
              {chart.lines.length > 0 && (
                <section className="card">
                  <h3>
                    SAVED LINES · {chart.lines.filter((x) => x.visible).length}{" "}
                    OF {chart.lines.length} SHOWN
                  </h3>
                  {chart.lines.map((line) => (
                    <div className="line-row" key={line.id}>
                      <span
                        className="swatch"
                        style={{ background: line.color_hex }}
                      />
                      <span className="identity">
                        <strong>{line.name}</strong>
                        <small>
                          SMA ({line.period} days) · {line.target_frequency}{" "}
                          signals / year{line.history_start && <small>Calculated from {historyLabel(line)}</small>}
                        </small>
                      </span>
                      <button
                        className="text"
                        onClick={() => setEdit({ ...line })}
                      >
                        Edit
                      </button>
                      <Toggle
                        checked={line.visible}
                        label={"Show " + line.name}
                        onChange={(visible) =>
                          changeLine(line, { visible }).catch(fail)
                        }
                      />
                    </div>
                  ))}
                  <p className="small">
                    The switch shows or hides a line on the chart. Hidden lines
                    can still send alerts.
                  </p>
                </section>
              )}
              {chart.backtest && (
                <section className="card backtest">
                  <div className="backtest-title">
                    <h2>Backtest</h2>
                    <span className="small">$100 per buy</span>
                  </div>
                  <p className="muted">
                    Three ways to make the same number of buys over the same
                    period.
                  </p>
                  <div className="segments">
                    {["1Y", "3Y", "5Y", "Max", "Custom"].map((value) => (
                      <button
                        key={value}
                        aria-pressed={horizon === value}
                        onClick={() => backtest(value)}
                      >
                        {value}
                      </button>
                    ))}
                  </div>
                  {horizon === "Custom" && (
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        backtest("Custom", years);
                      }}
                    >
                      <label>
                        Years of history
                        <input
                          type="number"
                          min="0.01"
                          step="any"
                          value={years}
                          onChange={(e) => setYears(e.target.value)}
                        />
                      </label>
                      <button>Apply</button>
                    </form>
                  )}
                  <p className="backtest-summary">
                    {chart.backtest.rows[0].indices.length} buys each ·{" "}
                    {chart.backtest.span}
                  </p>
                  {chart.backtest.rows.map((row, i) => {
                    const prefix = "$";
                    const largest = Math.max(
                      1,
                      ...chart.backtest.rows.map((x) => x.ending_value),
                    );
                    const change = row.ending_value - row.invested;
                    const comparison = i
                      ? row.difference === null
                        ? "N/A vs crossings"
                        : `${row.difference >= 0 ? "+" : ""}${row.difference.toFixed(1)}% vs crossings`
                      : row.return_percent === null
                        ? "N/A"
                        : `${row.return_percent >= 0 ? "+" : ""}${row.return_percent.toFixed(1)}% on contributions`;
                    const value = i ? row.difference : row.return_percent;
                    return (
                      <div className="backtest-row" key={row.key}>
                        <div>
                          <span>
                            <strong>
                              {
                                [
                                  "At upward crossings",
                                  "At equal intervals",
                                  "At random dates",
                                ][i]
                              }
                            </strong>
                            <small>
                              {
                                [
                                  `Your ${
                                    chart.lines.find(
                                      (saved) =>
                                        saved.period === chart.result.period && sameHistory(saved,chart.result),
                                    )?.name ||
                                    `SMA (${chart.result.period} days)`
                                  } signals`,
                                  "Regular buys, evenly spaced",
                                  "Most common of 500 samples",
                                ][i]
                              }
                            </small>
                          </span>
                          <span className="backtest-value">
                            <strong>
                              {prefix}
                              {Math.round(row.ending_value).toLocaleString(
                                "en-US",
                              )}
                            </strong>
                            <small
                              className={
                                value === null || value === 0
                                  ? ""
                                  : value < 0
                                    ? "negative"
                                    : "positive"
                              }
                            >
                              {comparison}
                            </small>
                          </span>
                        </div>
                        <div className={"bar" + (i ? " secondary" : "")}>
                          <span
                            style={{
                              width: `${(100 * row.ending_value) / largest}%`,
                            }}
                          />
                        </div>
                        <p className="small">
                          {row.invested
                            ? `${change >= 0 ? "+" : "−"}${prefix}${Math.round(Math.abs(change)).toLocaleString("en-US")} ${change >= 0 ? "gain" : "loss"} on ${prefix}${Math.round(row.invested).toLocaleString("en-US")} contributed`
                            : "No buys in this period"}
                        </p>
                      </div>
                    );
                  })}
                  <div className="backtest-stat">
                    <strong>
                      {chart.backtest.outperformance === null
                        ? "—"
                        : `${chart.backtest.outperformance.toFixed(0)}%`}
                    </strong>
                    <p>
                      {chart.backtest.outperformance === null
                        ? "No upward crossings in this period; no purchase comparison is available."
                        : "of the 500 random samples paid a higher average price than the crossing buys."}
                    </p>
                  </div>
                  <p className="small">
                    Excludes fees, taxes and currency moves. An estimate from
                    past prices, not a forecast.
                  </p>
                  <details>
                    <summary>All upward crossings</summary>
                    {chart.result.events.map((event, i) => (
                      <p key={i}>
                        {chart.dates[event.index] ||
                          `Session ${event.index + 1}`}{" "}
                        · {money(event.price)}
                      </p>
                    ))}
                  </details>
                </section>
              )}
            </>
          ) : (
            <section className="empty">
              <h2>Explore a saved chart</h2>
              <p>Open a line from Home, or find a new security.</p>
              <button className="primary" onClick={() => navigate("search")}>
                Find a security
              </button>
            </section>
          ))}
        {tab === "alerts" && (
          <>
            <p>Choose which saved lines can notify you.</p>
            <PushControls
              push={state.push}
              storage={state.storage}
              onChange={() => localApi("state").then(setState)}
            />
            {state.cards.flatMap((card) =>
              card.lines.map((line) => (
                <section className="card" key={line.id}>
                  <h2>
                    {card.security.ticker} · {line.name}
                  </h2>
                  {line.history_start && <p className="small">Calculated from {historyLabel(line)}</p>}
                  <div className="line-row">
                    <span>
                      <strong>Enable this line for alerts</strong>
                    </span>
                    <Toggle
                      checked={line.push_enabled}
                      label={"Alerts for " + line.name}
                      onChange={(push_enabled) =>
                        mutate("line", { id: line.id, push_enabled })
                      }
                    />
                  </div>
                  {LINE_SIGNAL_TYPES.map(([field, setting, label]) => (
                    <div
                      className={
                        "line-row signal-type" +
                        (line.push_enabled && state.settings[setting]
                          ? ""
                          : " muted")
                      }
                      key={field}
                    >
                      <span>
                        {label}
                        {!state.settings[setting] && (
                          <small>Off for all lines in Settings</small>
                        )}
                      </span>
                      <Toggle
                        checked={Boolean(line[field])}
                        disabled={!line.push_enabled}
                        label={label + " for " + line.name}
                        onChange={(value) =>
                          mutate("line", { id: line.id, [field]: value })
                        }
                      />
                    </div>
                  ))}
                  <p className="small">
                    {line.push_enabled
                      ? "Each type also needs its master switch in Settings."
                      : "Turn on alerts for this line to choose signal types."}
                  </p>
                </section>
              )),
            )}
          </>
        )}
        {tab === "settings" && (
          <>
            <Signup />
            <section className="card">
              <h3>NOTIFICATION TYPES</h3>
              <p className="small">
                Master switches for all saved lines. Choose types for each line
                in Alerts.
              </p>
              {[
                [
                  "phone_buy",
                  "Buy signal",
                  "Adjusted close crosses above the saved line.",
                ],
                [
                  "phone_monitor",
                  "Impending buy · end of trading",
                  "Adjusted close is below the saved line. US 06:30, SG 18:30 SGT.",
                ],
                [
                  "phone_monitor_start",
                  "Impending buy · start of trading",
                  "Last eligible adjusted close is above the saved line. US 21:30, SG 09:00 SGT.",
                ],
              ].map(([key, label, description]) => (
                <div className="line-row" key={key}>
                  <span>
                    <strong>{label}</strong>
                    <small>{description}</small>
                  </span>
                  <Toggle
                    checked={Boolean(state.settings[key])}
                    label={label}
                    onChange={(value) => mutate("settings", { [key]: value })}
                  />
                </div>
              ))}
            </section>
            <section className="card">
              <h3>APPEARANCE</h3>
              <div className="segments">
                {["system", "light", "dark"].map((value) => (
                  <button
                    key={value}
                    aria-pressed={theme === value}
                    onClick={() => setTheme(value)}
                  >
                    {value[0].toUpperCase() + value.slice(1)}
                  </button>
                ))}
              </div>
            </section>
            <section className="card">
              <h3>SAVED LINES</h3>
              <button
                className="setting"
                onClick={async () => {
                  try {
                    const value =
                      backend.current === "local"
                        ? await api("export")
                        : {
                            version: 1,
                            cards: state.cards.map(({ security, lines }) => ({
                              security,
                              lines,
                            })),
                            settings: state.settings,
                          };
                    const blob = new Blob([JSON.stringify(value, null, 2)], {
                        type: "application/json",
                      }),
                      url = URL.createObjectURL(blob),
                      link = document.createElement("a");
                    link.href = url;
                    link.download = "sma-saved-lines.json";
                    link.click();
                    URL.revokeObjectURL(url);
                  } catch (error) {
                    fail(error);
                  }
                }}
              >
                Export saved parameters <span>↓</span>
              </button>
              {state.storage === "local" && (
                <label className="setting">
                  Import saved parameters
                  <input
                    aria-label="Import saved parameters"
                    type="file"
                    accept="application/json,.json"
                    onChange={async (event) => {
                      const file = event.target.files?.[0];
                      event.target.value = "";
                      if (!file) return;
                      try {
                        if (file.size > 1048576)
                          throw new Error(
                            "Choose a saved-parameters backup under 1 MB.",
                          );
                        if (
                          !confirm(
                            "Merge this backup with your saved lines? Existing matching lines are kept.",
                          )
                        )
                          return;
                        const next = await api(
                          "import",
                          JSON.parse(await file.text()),
                        );
                        setState(next);
                      } catch (error) {
                        fail(error);
                      }
                    }}
                  />
                </label>
              )}
              <button className="setting" onClick={() => navigate("archive")}>
                Archived lines <span>Restore ›</span>
              </button>
            </section>
            <section className="card">
              <h3>LEGAL</h3>
              <p>
                This app is for personal use only and is not financial advice.
                It does not guarantee profits or future performance. Past
                results do not predict future results, and you are responsible
                for your own investment decisions.
              </p>
            </section>
            <p className="center">Version {state.version}</p>
          </>
        )}
        {tab === "archive" && (
          <>
            {state.archive.length === 0 && <p>No archived lines.</p>}
            {state.archive.map((line) => (
              <section className="card" key={line.id}>
                <h2>{line.name}</h2>
                {line.history_start && <p className="small">Calculated from {historyLabel(line)}</p>}
                <p>
                  {line.counter} · {line.target_frequency} signals / year
                </p>
                <button onClick={() => mutate("restore", { id: line.id })}>
                  Restore
                </button>
              </section>
            ))}
          </>
        )}
        {tab === "log" && (
          <>
            <button
              onClick={() =>
                navigator.clipboard
                  .writeText(JSON.stringify(events, null, 2))
                  .catch(fail)
              }
            >
              Copy diagnostic report
            </button>
            {events.map((event, i) => (
              <section className="card" key={i}>
                <strong>
                  {event.operation} · {event.status}
                </strong>
                <p>{event.detail}</p>
              </section>
            ))}
          </>
        )}
      </div>
      {!keyboard && (
        <nav aria-label="Main navigation">
          {["library", "results", "alerts", "settings"].map((key) => (
            <button
              key={key}
              aria-current={tab === key || (tab === "search" && key === "results") ? "page" : undefined}
              onClick={() => navigate(key)}
            >
              {labels[key]}
            </button>
          ))}
        </nav>
      )}
      {loading && (
        <div className="overlay">
          <section className="card">
            <MotionLogo />
            <h2>{tab === "search" ? "Loading security history…" : "Loading your saved lines…"}</h2>
          </section>
        </div>
      )}
      {job && (
        <Dialog label="Finding your SMA" onClose={cancel}>
          <section className="card">
            <MotionLogo />
            <h2>Finding your SMA line…</h2>
            <p>
              Matching about {target} upward crossings a year for{" "}
              {jobSecurity}.
            </p>
            <button onClick={cancel}>Cancel</button>
          </section>
        </Dialog>
      )}
      {historyPicker && (builder || chart) && <HistoryPicker data={tab==='search'?builder:chart} value={priceHistory} onApply={draft=>{if(selected)setEditingLine(selected);setPriceHistory(draft);}} onClose={()=>setHistoryPicker(false)}/>}
      {saveChoice && <Dialog label="This line is already saved" sheet onClose={()=>setSaveChoice(false)}><section className="sheet save-history-choice">
        <h2>This line is already saved</h2><p>You recalculated it with a different period. Choose what to do with the new result.</p>
        <button className="primary" onClick={()=>save('update')}>Update this line</button><p>Replaces {editingLine?.name} with SMA ({chart.result.period} days) · {historyLabel(chart.result)||'all available history'}. Its name, colour and alerts stay.</p>
        <button onClick={()=>save('new')}>Save as a new line</button><p>Keeps both. The new line starts with alerts on.</p>
        <button onClick={()=>setSaveChoice(false)}>Cancel</button>
      </section></Dialog>}
      {edit && (
        <Dialog label="Edit line" sheet onClose={() => setEdit(null)}>
          <section className="sheet">
            <div className="handle" />
            <div className="section-heading">
              <h2>Edit line</h2>
              <button
                className="text"
                onClick={async () => {
                  try {
                    if (
                      await changeLine(edit, {
                        name: edit.custom_name,
                        ...(edit.chosenColor !== undefined
                          ? { color: edit.chosenColor }
                          : {}),
                      })
                    )
                      setEdit(null);
                  } catch (e) {
                    fail(e);
                  }
                }}
              >
                Done
              </button>
            </div>
            <label>
              Name
              <input
                maxLength="60"
                value={edit.custom_name}
                placeholder={`SMA (${edit.period} days)`}
                onChange={(e) =>
                  setEdit({ ...edit, custom_name: e.target.value })
                }
              />
            </label>
            <p>Leave blank to use SMA ({edit.period} days).</p>
            <h3>Colour</h3>
            <div className="colors">
              {state.colors.map((color, i) => (
                <button
                  key={color.name}
                  aria-label={color.name}
                  aria-pressed={
                    (edit.color < 0 ? -edit.color - 1 : edit.color % 12) === i
                  }
                  onClick={() =>
                    setEdit({ ...edit, color: -i - 1, chosenColor: i })
                  }
                >
                  <span style={{ background: color.color }} />
                  {color.name}
                </button>
              ))}
            </div>
            <button
              className="negative"
              onClick={async () => {
                if (await changeLine(edit, { archive: true })) setEdit(null);
              }}
            >
              Archive line
            </button>
            <button onClick={() => setEdit(null)}>Cancel</button>
          </section>
        </Dialog>
      )}
    </main>
  );
}
