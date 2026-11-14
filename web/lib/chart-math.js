// Display/gesture math only. SMA values and intersections come from shared Python.
export const PLOT = { left: 68, top: 20, width: 550, height: 330, bottom: 350 };
export const finite = (value) => typeof value === "number" && Number.isFinite(value);
const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
export function ranges(count, dates = []) {
  const covers = (years) => dates.length
    ? dates[0] <= new Date(Date.parse(dates.at(-1) + "T12:00:00Z") - years * 365 * 86400000).toISOString().slice(0, 10)
    : count >= years * 252;
  return ["3M", "6M", "9M", "1Y", ...[3, 5].filter(covers).map((n) => `${n}Y`), "Max"];
}
export function presetBounds(count, dates, label) {
  const last = Math.max(0, count - 1);
  if (label === "Max" || count < 2) return [0, last];
  if (!dates.length) return [Math.max(0, count - parseInt(label) * (label.endsWith("M") ? 21 : 252)), last];
  const cutoff = new Date(dates.at(-1) + "T12:00:00Z");
  if (label.endsWith("Y")) cutoff.setUTCDate(cutoff.getUTCDate() - parseInt(label) * 365);
  else {
    const day = cutoff.getUTCDate();
    cutoff.setUTCDate(1);
    cutoff.setUTCMonth(cutoff.getUTCMonth() - parseInt(label));
    cutoff.setUTCDate(Math.min(day, new Date(Date.UTC(cutoff.getUTCFullYear(), cutoff.getUTCMonth() + 1, 0)).getUTCDate()));
  }
  const found = dates.findIndex((date) => date >= cutoff.toISOString().slice(0, 10));
  return [found < 0 ? last : found, last];
}
export function plottedLines(chart) {
  const result = chart.result;
  const lines = chart.lines.filter((line) => line.visible).map((line) => ({
    ...line, key: `saved-${line.id}`, name: line.name || `SMA (${line.period} days)`,
    color: line.color_hex || "#FFBD5C",
    events: line.events || (result?.period === line.period ? result.events : []) || [],
  }));
  if (result && !chart.lines.some((line) => line.period === result.period))
    lines.push({ ...result, key: "active", name: `SMA (${result.period} days)`, color: "#FFBD5C" });
  return lines;
}
export function limits(prices, lines, [start, end]) {
  let low = Infinity, high = -Infinity;
  for (const values of [prices, ...lines.map((line) => line.sma)])
    for (let i = Math.max(0, Math.floor(start)); i <= Math.min(values.length - 1, Math.ceil(end)); i++)
      if (finite(values[i])) { low = Math.min(low, values[i]); high = Math.max(high, values[i]); }
  if (!finite(low)) return null;
  const margin = Math.max((high - low) * .13, .01);
  return [low - margin, high + margin];
}
export function visibleChange(prices, [start, end]) {
  let first, last;
  for (let i = Math.max(0, Math.ceil(start)); i <= Math.min(prices.length - 1, Math.floor(end)); i++)
    if (finite(prices[i])) { first ??= prices[i]; last = prices[i]; }
  return finite(first) && finite(last) ? { delta: last - first, percent: first ? (last - first) / first * 100 : null } : null;
}
export function nearestSession(prices, [start, end], fraction) {
  const raw = start + clamp(fraction, 0, 1) * (end - start), floor = Math.floor(raw);
  const target = raw - floor === .5 ? floor + floor % 2 : Math.round(raw); // Python round ties.
  let best = null;
  for (let i = Math.max(0, Math.ceil(start)); i <= Math.min(prices.length - 1, Math.floor(end)); i++)
    if (finite(prices[i]) && (best === null || Math.abs(i - target) < Math.abs(best - target))) best = i;
  return best;
}
export function pinchBounds(count, initial, anchor, fraction, scale) {
  if (count < 2 || !finite(scale) || scale <= 0) return initial;
  const span = clamp((initial[1] - initial[0]) / scale, 1, count - 1);
  const start = clamp(anchor - fraction * span, 0, count - 1 - span);
  return [start, start + span];
}
const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function fullDate(value) {
  if (!value) return "—";
  const [year, month, day] = value.split("-").map(Number);
  return `${day} ${monthNames[month - 1]} ${year}`;
}
export function dateTicks(dates, [start, end], width, measure = (label) => label.length * 9, gap = 12) {
  const months = [], years = [];
  let previousMonth, previousYear;
  for (let index = Math.max(0, Math.ceil(start)); index <= Math.min(dates.length - 1, Math.floor(end)); index++) {
    const [year, month] = dates[index].split("-").map(Number), serial = year * 12 + month - 1;
    if (serial !== previousMonth) { months.push({ index, year, month, serial }); previousMonth = serial; }
    if (year !== previousYear) { years.push({ index, year, month, serial: year }); previousYear = year; }
  }
  function layout(items, stride, monthly) {
    if (!items.length) return [];
    const chosen = [];
    for (const item of items.filter((row) => (row.serial - items[0].serial) % stride === 0)) {
      const label = monthly ? `${monthNames[item.month - 1]} ${item.year}` : String(item.year), size = measure(label);
      const center = clamp((item.index - start) / Math.max(1, end - start) * width, size / 2, width - size / 2);
      if (size > width || (chosen.length && center - size / 2 < chosen.at(-1).center + chosen.at(-1).width / 2 + gap)) return null;
      chosen.push({ ...item, label, center, width: size });
    }
    return chosen;
  }
  for (const stride of [1, 2, 3, 4, 6]) {
    const ticks = layout(months, stride, true);
    if (ticks && (ticks.length >= 2 || months.length === 1)) return ticks;
  }
  for (const stride of [1, 2, 3, 5, 10, 20, 50, 100, 200]) {
    const ticks = layout(years, stride, false);
    if (ticks?.length) return ticks;
  }
  return [];
}
