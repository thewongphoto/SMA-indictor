"use client";
import { useEffect, useRef, useState } from "react";
import Chart from "./chart";
import Signup from "./signup";
import Dialog from "./dialog";
import { stored, clearSnapshots } from "./cache";

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
  version: "0.14.2",
};
const money = (value) =>
  Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
function Logo({ security }) {
  return security?.logo_url ? (
    <img className="company-logo" src={security.logo_url} alt="" />
  ) : (
    <span className="company-logo fallback">{security?.name?.[0] || "S"}</span>
  );
}
function MotionLogo() {
  return (
    <div className="motion-logo">
      <img src="/app-icon.png" alt="SMA Stock Analyzer" />
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
    [auth, setAuth] = useState(null),
    [password, setPassword] = useState(""),
    [loading, setLoading] = useState(true);
  const [error, setError] = useState(""),
    [offline, setOffline] = useState(false),
    [expanded, setExpanded] = useState({}),
    [query, setQuery] = useState(""),
    [submitted, setSubmitted] = useState(""),
    [matches, setMatches] = useState([]),
    [searching, setSearching] = useState(false);
  const [chart, setChart] = useState(null),
    [target, setTarget] = useState(4),
    [custom, setCustom] = useState(false),
    [job, setJob] = useState(null),
    [edit, setEdit] = useState(null),
    [horizon, setHorizon] = useState("Max"),
    [years, setYears] = useState(3),
    [theme, setTheme] = useState("system"),
    [events, setEvents] = useState([]),
    [keyboard, setKeyboard] = useState(false),
    [standalone, setStandalone] = useState(false);
  const generation = useRef(0),
    jobRef = useRef(null);
  async function api(path, body, method) {
    const response = await fetch("/api/" + path, {
      method: method || (body ? "POST" : "GET"),
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    const value = await response.json();
    if (response.status === 401) setAuth(false);
    if (!response.ok) throw new Error(value.error || "Request failed");
    return value;
  }
  async function refresh() {
    const value = await api("state");
    setState(value);
    setAuth(true);
    await stored("state", value);
    return value;
  }
  useEffect(() => {
    setWelcome(!localStorage.getItem("sma-welcome-done"));
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
    connection();
    window.addEventListener("online", connection);
    window.addEventListener("offline", connection);
    window.addEventListener("popstate", back);
    stored("state")
      .then((value) => {
        if (value) {
          setState(value);
          if (!navigator.onLine) setAuth(true);
        }
      })
      .catch(() => {});
    refresh()
      .catch((error) => {
        if (navigator.onLine) setError(error.message);
      })
      .finally(() => setLoading(false));
    if ("serviceWorker" in navigator)
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    return () => {
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
    setTab(next);
    setError("");
    history.pushState({ tab: next }, "", `#${next}`);
  }
  function fail(error) {
    setError(error.message || String(error));
  }
  async function login(event) {
    event.preventDefault();
    try {
      await api("login", { password });
      setPassword("");
      await refresh();
      setError("");
    } catch (e) {
      fail(e);
    }
  }
  async function openChart(security, line = null, cached = false) {
    const token = ++generation.current;
    setError("");
    setLoading(true);
    const cacheKey = `chart:${security.key}:${line?.period || 0}:${line?.target_frequency || 4}`;
    try {
      const value =
        offline || cached
          ? await stored(cacheKey)
          : await api("chart", {
              key: security.key,
              period: line?.period,
              target: line?.target_frequency,
            });
      if (!value)
        throw new Error(
          "Download this chart while online before opening it offline.",
        );
      if (token !== generation.current) return;
      setChart(value);
      setTarget(line?.target_frequency || 4);
      setHorizon("Max");
      setTab("results");
      history.pushState({ tab: "results" }, "", "#results");
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
  async function optimize() {
    const token = ++generation.current;
    setError("");
    setJob("pending");
    try {
      const result = await api("optimize", {
        key: chart.security.key,
        target: Number(target),
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
          await stored(
            `chart:${chart.security.key}:${next.data.result.period}:${target}`,
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
        horizon,
        years,
        cached: true,
      });
      if (token === generation.current) setChart(next);
      await stored(
        `chart:${next.security.key}:${next.result?.period || 0}:${next.result?.target || 4}`,
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
        horizon: value,
        years: newYears,
        cached: true,
      });
      if (token === generation.current) setChart(next);
    } catch (e) {
      if (token === generation.current) fail(e);
    }
  }
  async function save() {
    if (!chart?.result) return;
    const token = generation.current;
    await mutate("save", {
      key: chart.security.key,
      period: chart.result.period,
      target: chart.result.target,
    });
    const next = await api("chart", {
      key: chart.security.key,
      period: chart.result.period,
      target: chart.result.target,
      cached: true,
    });
    if (token === generation.current) setChart(next);
    await stored(
      `chart:${next.security.key}:${next.result.period}:${next.result.target}`,
      next,
    );
  }
  const selected = chart?.lines.find(
    (line) =>
      line.period === chart.result?.period &&
      line.target_frequency === chart.result?.target,
  );
  const below = state.cards.reduce((sum, card) => sum + card.below, 0);
  if (auth === false)
    return (
      <main className="login">
        <img src="/app-icon.png" alt="" />
        <h1>Your private SMA app</h1>
        <p>Sign in to open your saved lines.</p>
        <form onSubmit={login}>
          <label>
            Access password
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <button className="primary">Continue</button>
        </form>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
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
      <header>
        {!["library", "alerts", "settings"].includes(tab) && (
          <button className="text" onClick={() => navigate("library")}>
            ‹ Back
          </button>
        )}
        <h1>
          {tab === "results" && chart ? chart.security.ticker : labels[tab]}
        </h1>
        {tab === "library" ? (
          <button className="outline" onClick={() => navigate("search")}>
            + Find SMA
          </button>
        ) : tab === "results" && chart?.result && !guide ? (
          <button className="text" onClick={save} disabled={Boolean(selected)}>
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
            {welcome && (
              <Signup
                onDone={() => {
                  localStorage.setItem("sma-welcome-done", "1");
                  setWelcome(false);
                }}
              />
            )}
            {!standalone && (
              <div className="card install">
                <span>Add to Home Screen for a full-screen view.</span>
                <button
                  className="text"
                  onClick={() =>
                    alert(
                      "In Safari, tap Share, then Add to Home Screen. Server notifications are not enabled in this build.",
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
                          {card.price === null ? "—" : money(card.price)}
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
                            <strong>{line.name}</strong>
                            <small>
                              {line.target_frequency} signals / year · Alert{" "}
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
              US and Singapore listed stocks and ETFs. Press Search or Enter to
              look up matches.
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
                  openChart(
                    security,
                    state.cards.find((card) => card.counter === security.key)
                      ?.lines[0],
                  )
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
                    ? "Open ›"
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
            {!submitted && (
              <>
                <h3>RECENT SAVED SECURITIES</h3>
                {state.cards.map((card) => (
                  <button
                    className="search-result"
                    key={card.counter}
                    onClick={() =>
                      openChart(card.security, card.lines[0], true)
                    }
                  >
                    <Logo security={card.security} />
                    <span>{card.security.name}</span>
                  </button>
                ))}
                <p className="small">
                  Recent charts open from downloaded data without a new lookup.
                </p>
              </>
            )}
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
              <Chart chart={chart} colors={state.colors} />
              <section className="card">
                <h3>SIGNALS PER YEAR</h3>
                <div className="segments">
                  {[4, 6, 12].map((value) => (
                    <button
                      key={value}
                      aria-pressed={!custom && Number(target) === value}
                      onClick={() => {
                        setCustom(false);
                        setTarget(value);
                      }}
                    >
                      {value}
                    </button>
                  ))}
                  <button aria-pressed={custom} onClick={() => setCustom(true)}>
                    Custom
                  </button>
                </div>
                {custom && (
                  <label>
                    Upward crossings per year
                    <input
                      type="number"
                      min="1"
                      value={target}
                      onChange={(e) => setTarget(e.target.value)}
                    />
                  </label>
                )}
                <button
                  className="primary"
                  onClick={optimize}
                  disabled={offline || Boolean(job)}
                >
                  Find best SMA for {target} signals / year
                </button>
                <p className="small center">
                  Matches signal frequency, not profit.
                </p>
              </section>
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
                          signals / year
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
                    <span className="small">
                      {chart.preview ? "$" : "USD "}100 per buy
                    </span>
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
                    const prefix = chart.preview ? "$" : "USD ";
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
                                        saved.period === chart.result.period,
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
                              {Math.round(row.ending_value).toLocaleString("en-US")}
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
            <section className="notice">
              <strong>Server notifications are not enabled yet</strong>
              <p>
                Your preferences are saved. Delivery requires the production
                scheduler and Web Push service.
              </p>
            </section>
            {state.cards.flatMap((card) =>
              card.lines.map((line) => (
                <section className="card" key={line.id}>
                  <h2>
                    {card.security.ticker} · {line.name}
                  </h2>
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
              <h3>MARKET DATA</h3>
              <button className="setting" onClick={() => refresh().catch(fail)}>
                Refresh connection status <span>›</span>
              </button>
              <button
                className="setting"
                onClick={async () => {
                  try {
                    setEvents((await api("log")).events);
                    navigate("log");
                  } catch (e) {
                    fail(e);
                  }
                }}
              >
                Request log <span>View and copy ›</span>
              </button>
              <button
                className="setting"
                onClick={() => {
                  const blob = new Blob(
                    [
                      JSON.stringify(
                        {
                          version: 1,
                          cards: state.cards.map(({ security, lines }) => ({
                            security,
                            lines,
                          })),
                          settings: state.settings,
                        },
                        null,
                        2,
                      ),
                    ],
                    { type: "application/json" },
                  );
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "sma-saved-lines.json";
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                Export saved parameters <span>↓</span>
              </button>
              <button
                className="setting negative"
                onClick={async () => {
                  if (
                    confirm(
                      "Clear downloaded market data? Your saved SMA parameters are kept.",
                    )
                  ) {
                    await clearSnapshots();
                    await mutate("clear-cache", {});
                    setChart(null);
                  }
                }}
              >
                Clear downloaded data <span>Keeps saved SMAs ›</span>
              </button>
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
            <button
              onClick={async () => {
                await api("logout", {});
                await clearSnapshots();
                setState(defaultState);
                setChart(null);
                setAuth(false);
              }}
            >
              Sign out
            </button>
          </>
        )}
        {tab === "archive" && (
          <>
            {state.archive.length === 0 && <p>No archived lines.</p>}
            {state.archive.map((line) => (
              <section className="card" key={line.id}>
                <h2>{line.name}</h2>
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
              aria-current={tab === key ? "page" : undefined}
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
            <h2>Loading your saved lines…</h2>
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
              {chart?.security.ticker}.
            </p>
            <button onClick={cancel}>Cancel</button>
          </section>
        </Dialog>
      )}
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
