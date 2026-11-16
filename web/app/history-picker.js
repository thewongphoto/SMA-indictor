"use client";
import {useState} from "react";
import Dialog from "./dialog";
import {historyOf,historyLabel,historyPreset,historyReadout} from "../lib/history-window";
export function HistoryRow({data,value,onOpen}) {
  const custom=Boolean(value?.history_start);
  return <button type="button" className={`history-row${custom?' history-custom':''}`} onClick={onOpen} disabled={!data?.dates?.length}>
    <span><strong>Price history used{custom?' · custom':''}</strong><small>{custom?historyLabel(value):`All available${data?.dates?.length ? ` · ${data.dates[0].slice(0,4)} – ${data.dates.at(-1)}`:''}`}</small></span><span aria-hidden="true">›</span>
  </button>;
}
export default function HistoryPicker({data,value,onApply,onClose}) {
  const [draft,setDraft]=useState(historyOf(value)),[mode,setMode]=useState(value?.history_start?'custom':'all');
  let readout,error='';try{readout=historyReadout(data,draft);}catch(e){error=e.message;}
  const prices=data.prices,valid=prices.filter(Number.isFinite),low=Math.min(...valid),high=Math.max(...valid),den=Math.max(1,high-low);
  const path=prices.map((p,i)=>Number.isFinite(p)?`${i && Number.isFinite(prices[i-1])?'L':'M'}${i/Math.max(1,prices.length-1)*600},${110-(p-low)/den*95}`:'').join(' ');
  return <Dialog label="Price history used" sheet onClose={onClose}><section className="sheet history-sheet">
    <div className="handle"/><div className="section-heading"><h2>Price history used</h2><button className="text" onClick={onClose}>Cancel</button></div>
    <p>{data.security.ticker} · prices available from {data.dates[0]}</p>
    <svg className="history-mini" viewBox="0 0 600 120" role="img" aria-label="Price history with selected calculation window highlighted">
      <path d={path} fill="none" stroke="var(--price)" strokeWidth="2"/>
      {readout && <><rect x="0" y="0" width={readout.left/Math.max(1,prices.length-1)*600} height="120" fill="var(--bg)" opacity=".8"/><rect x={readout.right/Math.max(1,prices.length-1)*600} y="0" width={600-readout.right/Math.max(1,prices.length-1)*600} height="120" fill="var(--bg)" opacity=".8"/></>}
    </svg>
    <div className="history-presets">{[['all','All available',null],['10','Last 10 years',10],['5','Last 5 years',5],['3','Last 3 years',3]].map(([id,title,years])=><button key={id} aria-pressed={mode===id} onClick={()=>{setMode(id);setDraft(historyPreset(data.dates,years));}}>{title}</button>)}<button aria-pressed={mode==='custom'} onClick={()=>{setMode('custom');if(!draft.history_start)setDraft({history_start:data.dates[0],history_end:data.dates.at(-1)});}}>Custom dates</button></div>
    {mode==='custom' && <div className="date-fields">{[['From','history_start'],['To','history_end']].map(([title,key])=><label key={key}>{title}<input type="date" min={data.dates[0]} max={data.dates.at(-1)} value={draft[key]} aria-invalid={Boolean(error)} onChange={e=>setDraft({...draft,[key]:e.target.value})}/></label>)}</div>}
    <p className={error?'negative':''} role="status">{error || readout.text}</p>
    <p className="small">A saved line keeps these exact dates. They do not move forward over time.</p>
    {draft.history_start && <button className="text" onClick={()=>{setMode('all');setDraft(historyOf());}}>Use all available history</button>}
    <button className="primary" disabled={Boolean(error)} onClick={()=>{onApply(draft);onClose();}}>Use this history</button>
  </section></Dialog>;
}
