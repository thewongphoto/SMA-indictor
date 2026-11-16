export const historyOf = (value = {}) => ({ history_start: value?.history_start || "", history_end: value?.history_end || "" });
export function checkedHistory(value = {}) {
  if(value && [value.history_start,value.history_end].some(x=>x!==undefined && x!==null && typeof x!=="string"))throw new Error("Use valid From and To dates.");
  const h = historyOf(value), {history_start:a,history_end:b}=h;
  if (!a && !b) return h;
  const valid = (s) => typeof s === "string" && /^\d{4}-\d{2}-\d{2}$/.test(s) && Number.isFinite(Date.parse(s)) && new Date(s).toISOString().slice(0,10) === s;
  if (!valid(a) || !valid(b) || a>b) throw new Error("Choose valid From and To dates, with From before To.");
  return h;
}
export const sameHistory = (a,b) => historyOf(a).history_start===historyOf(b).history_start && historyOf(a).history_end===historyOf(b).history_end;
export const historyKey = (value) => { const h=historyOf(value);return h.history_start ? `|${h.history_start}|${h.history_end}` : ""; };
export function historyLabel(value, short=false) {
  const h=historyOf(value);if(!h.history_start)return "";
  if(short)return h.history_start.slice(0,4)===h.history_end.slice(0,4) ? `${h.history_start} – ${h.history_end}` : `${h.history_start.slice(0,4)}–${h.history_end.slice(0,4)}`;
  const fmt=s=>new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(s));
  return `${fmt(h.history_start)} – ${fmt(h.history_end)}`;
}
export function historyPreset(dates, years=null) {
  if(years===null)return historyOf();
  return {history_start:dates[0] > new Date(Date.parse(dates.at(-1))-years*365*86400000).toISOString().slice(0,10) ? dates[0] : new Date(Date.parse(dates.at(-1))-years*365*86400000).toISOString().slice(0,10),history_end:dates.at(-1)};
}
export function historyReadout(data, value) {
  const h=checkedHistory(value), dates=data.dates||[], prices=data.prices||[];
  if(!dates.length)throw new Error("Download dated price history first.");
  if(h.history_start && (h.history_start<dates[0]||h.history_end>dates.at(-1)))throw new Error(`Choose dates between ${dates[0]} and ${dates.at(-1)}.`);
  const left=h.history_start ? dates.findIndex(d=>d>=h.history_start):0;
  let right=dates.length-1;while(right>=0 && h.history_end && dates[right]>h.history_end)right--;
  const count=right-left+1;
  if(left<0 || count<4)throw new Error("Choose at least 4 trading days so an SMA can warm up and be compared.");
  const cap=count<=756?Math.min(Math.floor(count/2),252):count-504;
  let run=0,comparisons=0;for(let i=left;i<=right;i++){run=Number.isFinite(prices[i])?run+1:0;if(run>=3)comparisons++;}
  if(comparisons<count-cap)throw new Error("Choose a wider period with enough consecutive complete closing prices.");
  return {left,right,count,text:`Uses ${count.toLocaleString()} trading days, ${historyLabel({history_start:dates[left],history_end:dates[right]})}`};
}
