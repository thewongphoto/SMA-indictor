"use client";
import {HistoryRow} from "./history-picker";
import CompanyLogo from "./company-logo";

// The builder and chart edit the same target, just as Android's two controls do.
export default function TargetPreference({ security, onSecurity, target, custom, onTarget, onCustom, onOptimize, disabled, calendar, data, history, onHistory, stale }) {
  return (
    <section className={`card target-preference${security ? " preference-builder" : ""}`}>
      {security && <>
        <h3>SELECTED SECURITY</h3>
        <button type="button" className="selected-security chart-identity" onClick={onSecurity}>
          <CompanyLogo security={security} />
          <strong>{security.name}</strong>
        </button>
      </>}
      <h3>{security ? "TARGET CROSSINGS" : "SIGNALS PER YEAR"}</h3>
      <form onSubmit={(event) => { event.preventDefault(); onOptimize(); }}>
        <div className="segments" role="group" aria-label="Target crossings per year">
          {[4, 6, 12].map((value) => (
            <button type="button" key={value} aria-pressed={!custom && Number(target) === value}
              onClick={() => onTarget(value)}>{value}</button>
          ))}
          <button type="button" aria-pressed={custom} onClick={onCustom}>Custom</button>
        </div>
        {custom && <label>
          Upward crossings per year
          <input type="number" inputMode="numeric" min="1" max={Number.MAX_SAFE_INTEGER}
            step="1" required value={target} onChange={(event) => onTarget(event.target.value, true)} />
        </label>}
        {calendar && <p className="small">1 year = 365 calendar days, including weekends and holidays.</p>}
        <HistoryRow data={data} value={history} onOpen={onHistory}/>
        <button className="primary" disabled={disabled}>{stale ? "Recalculate for" : "Find best SMA for"} {target} signals / year</button>
      </form>
      <p className="small center">Matches signal frequency, not profit.</p>
    </section>
  );
}
