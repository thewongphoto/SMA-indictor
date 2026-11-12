"use client";
import { useEffect, useRef, useState } from "react";
export default function Chart({ chart, colors }) {
  const [range, setRange] = useState("1Y"),
    [bounds, setBounds] = useState([0, 1]),
    [inspect, setInspect] = useState(null);
  const pointers = useRef(new Map()),
    pinch = useRef(null),
    svg = useRef();
  const count = chart.prices.length;
  function preset(value) {
    setRange(value);
    setInspect(null);
    let first = 0;
    if (value !== "Max" && chart.dates.length) {
      const end = new Date(chart.dates.at(-1) + "T12:00:00Z");
      if (value.endsWith("M")) {
        const day = end.getUTCDate();
        end.setUTCDate(1);
        end.setUTCMonth(end.getUTCMonth() - parseInt(value));
        end.setUTCDate(
          Math.min(
            day,
            new Date(
              Date.UTC(end.getUTCFullYear(), end.getUTCMonth() + 1, 0),
            ).getUTCDate(),
          ),
        );
      } else end.setUTCDate(end.getUTCDate() - 365 * parseInt(value));
      first = Math.max(
        0,
        chart.dates.findIndex((date) => date >= end.toISOString().slice(0, 10)),
      );
    } else if (value !== "Max")
      first = Math.max(
        0,
        count -
          (value.endsWith("M") ? parseInt(value) * 21 : parseInt(value) * 252),
      );
    setBounds([first, Math.max(first + 1, count - 1)]);
  }
  useEffect(() => {
    preset("1Y");
  }, [chart.security.key, count]);
  const [start, end] = bounds,
    lo = Math.max(0, Math.ceil(start)),
    hi = Math.min(count - 1, Math.floor(end));
  const active = chart.result;
  const lines = chart.lines.filter((line) => line.visible);
  const all = [
    { sma: chart.prices, color: "var(--price)", id: "price" },
    ...lines.map((line) => ({ ...line, color: line.color_hex || "#FFBD5C" })),
  ];
  if (active && !chart.lines.some((line) => line.period === active.period))
    all.push({ sma: active.sma, color: "#FFBD5C", id: "active" });
  const finite = all
    .flatMap((line) => line.sma.slice(lo, hi + 1))
    .filter((value) => Number.isFinite(value));
  const min = Math.min(...finite),
    max = Math.max(...finite),
    spread = max - min || 1;
  const x = (i) => 20 + ((i - start) / Math.max(1, end - start)) * 600,
    y = (value) => 220 - ((value - min) / spread) * 190;
  function path(values) {
    let open = false;
    return values
      .slice(lo, hi + 1)
      .map((value, i) => {
        if (!Number.isFinite(value)) {
          open = false;
          return "";
        }
        const segment = `${open ? "L" : "M"}${x(lo + i).toFixed(1)},${y(value).toFixed(1)}`;
        open = true;
        return segment;
      })
      .join(" ");
  }
  function pointer(event) {
    const rect = svg.current.getBoundingClientRect();
    pointers.current.set(event.pointerId, event.clientX);
    if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()],
        distance = Math.abs(a - b);
      if (!pinch.current) pinch.current = { distance, bounds };
      else {
        const old = pinch.current,
          span = Math.min(
            count - 1,
            Math.max(
              10,
              ((old.bounds[1] - old.bounds[0]) * old.distance) /
                Math.max(1, distance),
            ),
          ),
          middle = (old.bounds[0] + old.bounds[1]) / 2;
        const left = Math.max(0, Math.min(count - 1 - span, middle - span / 2));
        setBounds([left, left + span]);
        setRange("Custom");
      }
    } else
      setInspect(
        Math.max(
          lo,
          Math.min(
            hi,
            Math.round(
              start +
                ((event.clientX - rect.left) / rect.width) * (end - start),
            ),
          ),
        ),
      );
  }
  const visiblePrices = chart.prices.slice(lo, hi + 1).filter(Number.isFinite);
  const first = visiblePrices[0],
    last = visiblePrices.at(-1),
    delta =
      Number.isFinite(first) && Number.isFinite(last) ? last - first : null;
  const percentage = delta !== null && first ? (delta / first) * 100 : null;
  const fmt = (value) =>
    Number.isFinite(value)
      ? value.toLocaleString(undefined, {
          maximumFractionDigits: 2,
          minimumFractionDigits: 2,
        })
      : "—";
  return (
    <section className="chart-section">
      <div className="price">
        {chart.currency} {fmt(chart.prices.at(-1))}
      </div>
      <p className={delta < 0 ? "negative" : delta > 0 ? "positive" : "muted"}>
        {delta === null
          ? "No comparable closes"
          : `${delta < 0 ? "▼" : delta > 0 ? "▲" : "—"} ${fmt(delta)} (${fmt(percentage)}%) · ${range === "Max" ? "all history" : range === "Custom" ? "selected dates" : `past ${range}`}`}
      </p>
      {active && (
        <div className="card status">
          <strong>
            Price is{" "}
            {active.state === "On line" ? "on" : active.state.toLowerCase()} its{" "}
            {active.period}-day line
          </strong>
          <p>
            About {active.frequency.toFixed(2)} upward crossings a year.
            {active.events.length > 0 && chart.dates.length > 0
              ? ` Last crossed above on ${chart.dates[active.events.at(-1).index]}.`
              : ""}
          </p>
        </div>
      )}
      <svg
        ref={svg}
        viewBox="0 0 640 260"
        role="img"
        aria-label="Adjusted daily closing prices and saved SMA lines"
        onPointerDown={(event) => {
          event.currentTarget.setPointerCapture(event.pointerId);
          pointer(event);
        }}
        onPointerMove={(event) => {
          if (pointers.current.has(event.pointerId)) pointer(event);
        }}
        onPointerUp={(event) => {
          pointers.current.delete(event.pointerId);
          pinch.current = null;
        }}
        onPointerCancel={(event) => {
          pointers.current.delete(event.pointerId);
          pinch.current = null;
        }}
        onDoubleClick={() => preset("Max")}
      >
        {[0, 1, 2].map((i) => (
          <line
            key={i}
            x1="20"
            x2="620"
            y1={30 + i * 95}
            y2={30 + i * 95}
            stroke="var(--divider)"
          />
        ))}
        {all.map((line) => (
          <path
            key={line.id}
            d={path(line.sma)}
            fill="none"
            stroke={line.color}
            strokeWidth={line.id === "price" ? 2 : 3}
          />
        ))}
        {inspect !== null && (
          <line
            x1={x(inspect)}
            x2={x(inspect)}
            y1="20"
            y2="225"
            stroke="var(--text-muted)"
            strokeDasharray="4 4"
          />
        )}
        <text x="20" y="250" fill="var(--text-muted)" fontSize="28">
          {chart.dates[lo] || `Session ${lo + 1}`}
        </text>
        <text
          x="620"
          y="250"
          textAnchor="end"
          fill="var(--text-muted)"
          fontSize="28"
        >
          {chart.dates[hi] || `Session ${hi + 1}`}
        </text>
      </svg>
      {inspect !== null && (
        <p aria-live="polite">
          {chart.dates[inspect] || `Session ${inspect + 1}`} · {chart.currency}{" "}
          {fmt(chart.prices[inspect])}
        </p>
      )}
      <div className="segments ranges">
        {["3M", "6M", "9M", "1Y", "3Y", "5Y", "Max"].map((value) => (
          <button
            key={value}
            aria-pressed={range === value}
            onClick={() => preset(value)}
          >
            {value}
          </button>
        ))}
      </div>
      <p className="muted small">
        {chart.preview
          ? "Example daily prices"
          : "Adjusted daily close · dividends and splits included"}
        . Pinch to zoom; touch to inspect.
      </p>
    </section>
  );
}
