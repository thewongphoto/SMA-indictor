import {test} from 'node:test';
import assert from 'node:assert/strict';
import {checkedHistory,historyKey,historyLabel,historyPreset,historyReadout,sameHistory} from '../lib/history-window.js';

test('custom date validation rejects incomplete, impossible, reversed and non-text dates',()=>{
  for(const value of [
    {history_start:'2024-02-30',history_end:'2025-01-01'},
    {history_start:'2025-01-01',history_end:'2024-01-01'},
    {history_end:'2024-01-01'}, {history_start:false}, {history_start:0},
  ]) assert.throws(()=>checkedHistory(value));
  assert.deepEqual(checkedHistory({}),{history_start:'',history_end:''});
  assert.equal(historyKey({}),''); // Retain existing default cache/event identities.
  assert.ok(sameHistory({}, {history_start:'',history_end:''}));
  assert.ok(!sameHistory({}, {history_start:'2024-01-01',history_end:'2025-01-01'}));
});

test('presets resolve to exact frozen dates; the live readout uses observed sessions and actual gaps',()=>{
  const dates=Array.from({length:1500},(_,i)=>new Date(Date.UTC(2020,0,1)+i*86400000).toISOString().slice(0,10));
  const data={dates,prices:dates.map((_,i)=>100+Math.sin(i))};
  const frozen=historyPreset(dates,3),end=dates.at(-1);
  dates.push('2030-01-01');data.prices.push(101);
  assert.equal(frozen.history_end,end);
  assert.equal(historyReadout(data,frozen).count,1096);
  assert.throws(()=>historyReadout(data,{history_start:dates[0],history_end:dates[1]}),/4 trading days/);
  assert.throws(()=>historyReadout({...data,prices:dates.map(()=>null)},frozen),/complete closing prices/);
  assert.throws(()=>historyReadout(data,{history_start:'2010-01-01',history_end:end}),/between/);
  assert.equal(historyLabel({history_start:'2019-01-01',history_end:'2024-12-31'},true),'2019–2024');
});
