"use client";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import CompanyLogo from "./company-logo";
import { PLOT, finite, ranges, presetBounds, plottedLines, limits, visibleChange, nearestSession, pinchBounds, dateTicks, fullDate } from "../lib/chart-math";
const format = (value, digits = 2) => finite(value) ? value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits }) : "—";
const PLUS = "M-3-10H3V-3H10V3H3V10H-3V3H-10V-3H-3Z";
function Arrow({ direction }) {
  return <svg className="change-arrow" viewBox="0 0 12 12" aria-hidden="true"><path d={direction < 0 ? "M0 1H12L6 11Z" : direction > 0 ? "M0 11H12L6 1Z" : "M0 5H12V7H0Z"} fill="currentColor" /></svg>;
}
export default function Chart({ chart }) {
  const count = chart.prices.length;
  const calendarDates = chart.preview ? [] : chart.dates;
  const [range, setRange] = useState("1Y"), [bounds, setBounds] = useState(() => presetBounds(count, calendarDates, "1Y")), [inspect, setInspect] = useState(null);
  const svg = useRef(null), pointers = useRef(new Map()), pinch = useRef(null), pinched = useRef(false);
  const baseRange = useRef("1Y");
  const clip = useId();
  const currentBounds = useRef(bounds); currentBounds.current = bounds;
  const active = chart.result;
  const lines = useMemo(() => plottedLines(chart), [chart]);
  const extrema = useMemo(() => limits(chart.prices, lines, bounds), [chart.prices, lines, bounds]);
  const [start, end] = bounds, lo = Math.max(0, Math.ceil(start)), hi = Math.min(count - 1, Math.floor(end));
  const [low, high] = extrema || [0, 1];
  const x = (index) => PLOT.left + (index - start) / Math.max(1, end - start) * PLOT.width;
  const y = (value) => PLOT.bottom - (value - low) / (high - low) * PLOT.height;
  function preset(value) {
    pointers.current.clear(); pinch.current = null; pinched.current = false;
    baseRange.current = value;
    setRange(value); setInspect(null); setBounds(presetBounds(count, calendarDates, value));
  }
  useEffect(() => { preset("1Y"); }, [chart.security.key, count]);
  const paths = useMemo(() => {
    function path(values) {
      const parts = []; let open = false;
      for (let i = Math.max(0, Math.floor(start)); i <= Math.min(values.length - 1, Math.ceil(end)); i++) {
        if (!finite(values[i])) { open = false; continue; }
        parts.push(`${open ? "L" : "M"}${x(i).toFixed(2)},${y(values[i]).toFixed(2)}`); open = true;
      }
      return parts.join(" ");
    }
    return [{ key: "price", name: "Adj. close", sma: chart.prices, color: "var(--price)" }, ...lines].map((line) => ({ ...line, path: path(line.sma) }));
  }, [chart.prices, lines, start, end, low, high]);
  const ticks = useMemo(() => dateTicks(chart.dates, bounds, PLOT.width), [chart.dates, bounds]);
  const change = visibleChange(chart.prices, bounds), direction = Math.sign(change?.delta || 0);
  const latest = useMemo(() => {
    for (let i = chart.prices.length - 1; i >= 0; i--) if (finite(chart.prices[i])) return chart.prices[i];
    return null;
  }, [chart.prices]);
  const selectedName = chart.lines.find((line) => line.period === active?.period)?.name || `SMA (${active?.period} days)`;
  const inspectionLines = active ? [{ key: "selected", name: selectedName, sma: active.sma, color: lines.find((line) => line.period === active.period)?.color || "#FFBD5C" }, ...lines.filter((line) => line.period !== active.period)] : lines;
  function point(clientX, clientY) {
    const matrix = svg.current?.getScreenCTM();
    if (!matrix) return null;
    const p = svg.current.createSVGPoint(); p.x = clientX; p.y = clientY;
    return p.matrixTransform(matrix.inverse());
  }
  function pointer(event) {
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const fingers = [...pointers.current.values()];
    if (fingers.length >= 2) {
      pinched.current = true; setInspect(null);
      const [a, b] = fingers, distance = Math.hypot(a.x - b.x, a.y - b.y), mid = point((a.x + b.x) / 2, (a.y + b.y) / 2);
      if (!mid) return;
      const fraction = Math.max(0, Math.min(1, (mid.x - PLOT.left) / PLOT.width));
      if (!pinch.current) {
        if (distance < 12) return;
        const initial = currentBounds.current;
        pinch.current = { distance, initial, anchor: initial[0] + fraction * (initial[1] - initial[0]) };
      } else {
        const before = pinch.current;
        const next = pinchBounds(count, before.initial, before.anchor, fraction, distance / before.distance);
        const base = presetBounds(count, calendarDates, baseRange.current);
        setBounds(next);
        setRange(next.every((value, index) => Math.abs(value - base[index]) < 1e-8) ? baseRange.current : "Custom");
      }
    } else if (!pinched.current) {
      const position = point(event.clientX, event.clientY);
      if (position) setInspect(nearestSession(chart.prices, currentBounds.current, (position.x - PLOT.left) / PLOT.width));
    }
  }
  function finish(event) {
    pointers.current.delete(event.pointerId);
    if (!pointers.current.size) { pinch.current = null; pinched.current = false; }
  }
  const crossingDate = active?.events?.length ? chart.dates[active.events.at(-1).index] : null;
  const inspectX = inspect === null ? 0 : x(inspect), inspectY = inspect === null ? 0 : y(chart.prices[inspect]);
  const tipHeight = 24 + 24 * (inspectionLines.length + 2), tipWidth = 300;
  const tipX = Math.max(PLOT.left, Math.min(PLOT.left + PLOT.width - tipWidth, inspectX + 16));
  const tipY = Math.max(PLOT.top, Math.min(PLOT.bottom - tipHeight, inspectY + 12));
  return <section className="chart-section">
    <div className="chart-identity"><CompanyLogo security={chart.security} /><strong>{chart.security.name}</strong></div>
    <div className="price">{finite(latest) ? `$${format(latest)}` : "—"}</div>
    <div className={`chart-change ${direction < 0 ? "negative" : direction > 0 ? "positive" : "muted"}`}>
      {change ? <><span><Arrow direction={direction} />${format(Math.abs(change.delta))}</span><span className="change-percent"><Arrow direction={direction} />{format(Math.abs(change.percent))}%</span></> : <span>No comparable closes</span>}
      <small className="change-period">{range === "Custom" ? `${fullDate(chart.dates[lo])} – ${fullDate(chart.dates[hi])}` : range === "Max" ? "ALL HISTORY" : `PAST ${range}`}</small>
    </div>
    {active && <div className="card status"><strong>Price is {active.state === "On line" ? "on" : active.state.toLowerCase()} its {active.period}-day line</strong><p>{crossingDate ? `It crossed above on ${fullDate(crossingDate)}. ` : ""}This line has been crossed upward about {active.frequency.toFixed(1)} times a year.</p></div>}
    <div className="card chart-panel">
      <p className="chart-caption">{chart.preview ? "Example daily prices" : `${chart.currency || ""} adjusted daily close`}<br />{chart.preview ? "Simulated data" : "Dividends and splits included"}</p>
      <svg className="chart-plot" ref={svg} viewBox="0 0 640 430" role="img" aria-label="Adjusted daily closing prices and saved SMA lines"
        onPointerDown={(event) => {
          if (event.pointerType === "mouse" && event.button !== 0) return;
          const p = point(event.clientX, event.clientY);
          if (!extrema || count < 2 || !p || p.x < PLOT.left || p.x > PLOT.left + PLOT.width || p.y < PLOT.top || p.y > PLOT.bottom) return;
          if (!pointers.current.size) pinched.current = false;
          event.currentTarget.setPointerCapture(event.pointerId); pointer(event);
        }}
        onPointerMove={(event) => { if (pointers.current.has(event.pointerId)) pointer(event); }}
        onPointerUp={finish} onPointerCancel={finish} onLostPointerCapture={finish}
        onDoubleClick={() => preset(baseRange.current)}>
        <defs><clipPath id={clip}><rect x={PLOT.left} y={PLOT.top} width={PLOT.width} height={PLOT.height} /></clipPath></defs>
        {extrema && <g className="chart-axes" aria-hidden="true">
          {[0, 1, 2, 3, 4].map((i) => {
            const value = low + (high - low) * i / 4, position = y(value);
            return <g key={i}><line x1={PLOT.left} x2={PLOT.left + PLOT.width} y1={position} y2={position} stroke="var(--divider)" /><text x="52" y={position + 6} textAnchor="end">{high - low < 5 ? value.toFixed(2) : value.toFixed(0)}</text></g>;
          })}
          {ticks.map((tick) => <g key={tick.index}><line x1={x(tick.index)} x2={x(tick.index)} y1={PLOT.top} y2={PLOT.bottom} stroke="var(--divider)" /><text x={PLOT.left + tick.center} y="382" textAnchor="middle">{tick.label}</text></g>)}
          <path d={`M${PLOT.left} ${PLOT.top}V${PLOT.bottom}H${PLOT.left + PLOT.width}`} fill="none" stroke="var(--text-muted)" />
          <text x="343" y="416" textAnchor="middle">Date</text><text transform="translate(17 185) rotate(-90)" textAnchor="middle">Price</text>
        </g>}
        {extrema ? <g clipPath={`url(#${clip})`}>
          {paths.map((line) => <path key={line.key} data-series={line.key} d={line.path} fill="none" stroke={line.color} strokeWidth={line.key === "price" ? 2.4 : line.period === active?.period ? 3.2 : 2} />)}
          {lines.flatMap((line) => (line.events || []).map((event, index) => {
            const at = event.position ?? event.index;
            return at >= start && at <= end && finite(event.price) ? <path data-crossing={line.key} data-position={at} key={`${line.key}-${index}`} d={PLUS} transform={`translate(${x(at)} ${y(event.price)})`} fill={line.color} stroke="#000" strokeWidth=".9" /> : null;
          }))}
          {inspect !== null && <g className="inspection-points"><line x1={inspectX} x2={inspectX} y1={PLOT.top} y2={PLOT.bottom} stroke="var(--text-muted)" /><circle cx={inspectX} cy={inspectY} r="5" fill="var(--price)" />{inspectionLines.map((line) => finite(line.sma[inspect]) && <circle key={line.key} cx={inspectX} cy={y(line.sma[inspect])} r="5" fill={line.color} />)}</g>}
        </g> : <text x="343" y="185" textAnchor="middle" className="chart-empty">No prices loaded. Choose a security to begin.</text>}
        {inspect !== null && <g className="chart-tooltip" aria-hidden="true" transform={`translate(${tipX} ${tipY})`}>
          <rect width={tipWidth} height={tipHeight} rx="8" fill="var(--control)" stroke="var(--border)" />
          <text x="12" y="26">Date: {fullDate(chart.dates[inspect])}</text><text x="12" y="50">Adj. close: ${format(chart.prices[inspect], 4)}</text>
          {inspectionLines.map((line, index) => <text key={line.key} x="12" y={74 + index * 24}>{line.name.length > 25 ? `${line.name.slice(0, 24)}…` : line.name}: {finite(line.sma[inspect]) ? `$${format(line.sma[inspect], 4)}` : "Unavailable"}</text>)}
        </g>}
        <rect className="plot-interaction" x={PLOT.left} y={PLOT.top} width={PLOT.width} height={PLOT.height} fill="transparent" />
      </svg>
      <div className="chart-legend"><span><i style={{ background: "var(--price)" }} />Adj. close{chart.currency ? ` (${chart.currency})` : ""}</span><span><svg viewBox="-12 -12 24 24" className="legend-plus" aria-hidden="true"><path d={PLUS} fill="var(--text-muted)" stroke="#000" strokeWidth=".9" /></svg>upward crossings</span>{lines.map((line) => <span key={line.key}><i style={{ background: line.color }} />{line.name}</span>)}</div>
      {inspect !== null && <div className="chart-inspection" role="status" aria-live="polite"><strong>{fullDate(chart.dates[inspect])}</strong><span>Adj. close: ${format(chart.prices[inspect], 4)}</span>{inspectionLines.map((line) => <span key={line.key}>{line.name}: {finite(line.sma[inspect]) ? `$${format(line.sma[inspect], 4)}` : "Unavailable (warm-up/gap)"}</span>)}</div>}
      <p className="small chart-touch-hint">Drag one finger to inspect closing and SMA values. Pinch with two fingers to zoom.</p>
    </div>
    <div className="segments ranges">{ranges(count, calendarDates).map((value) => <button key={value} aria-pressed={range === value} disabled={!count} onClick={() => preset(value)}>{value}</button>)}</div>
    {range === "Custom" && <button className="text chart-zoom-reset" onClick={() => preset(baseRange.current)}>Zoom out</button>}
  </section>;
}
