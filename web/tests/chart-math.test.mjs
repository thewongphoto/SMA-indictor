import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {readFileSync} from 'node:fs';
import {presetBounds,ranges,limits,visibleChange,nearestSession,pinchBounds,dateTicks,plottedLines} from '../lib/chart-math.js';
import {logoUrl} from '../lib/brand.js';
const root=fileURLToPath(new URL('../../',import.meta.url));
const native=spawnSync('python3',['-c',`import json
from datetime import date,timedelta
from sma_analyzer.viewport import ChartViewport,available_timelines
from sma_analyzer.axis import date_ticks
dates=[(date(2019,1,1)+timedelta(days=i)).isoformat() for i in range(2200)]
v=ChartViewport(len(dates));v.dates=dates
bounds={}
for label in available_timelines(len(dates),dates):
 v.show_timeline(label);bounds[label]=v.bounds
v.start,v.end=100.2,1400.7
print(json.dumps(dict(dates=dates,bounds=bounds,ticks=[dict(index=t.index,label=t.label,center=t.center,width=t.width) for t in date_ticks(dates,100.2,1400.7,550,lambda s:len(s)*9)],pinch=(v.pinch((100.2,1400.7),700,.3,1.7),v.bounds),limits=v.y_limits([100+i*.1 for i in range(2200)]))))`],{cwd:root,encoding:'utf8'});
if(native.status!==0)throw new Error(native.stderr);
const expected=JSON.parse(native.stdout);
test('calendar presets and available long ranges match native, including leap days',()=>{
 assert.deepEqual(ranges(expected.dates.length,expected.dates),Object.keys(expected.bounds));
 for(const [label,bounds]of Object.entries(expected.bounds))assert.deepEqual(presetBounds(expected.dates.length,expected.dates,label),bounds);
 assert.deepEqual(presetBounds(3,['2024-02-29','2024-05-30','2024-05-31'],'3M'),[0,2]);
 assert.deepEqual(ranges(50,[]),['3M','6M','9M','1Y','Max']);
});
test('non-overlapping month/year axis ticks match native placement',()=>{
 assert.deepEqual(dateTicks(expected.dates,[100.2,1400.7],550).map(({index,label,center,width})=>({index,label,center,width})),expected.ticks);
});
test('pinch preserves the native midpoint anchor and can reach one-session resolution',()=>{
 assert.deepEqual(pinchBounds(2200,[100.2,1400.7],700,.3,1.7),expected.pinch[1]);
 assert.deepEqual(pinchBounds(100,[0,99],50,.5,1000),[49.5,50.5]);
 assert.deepEqual(pinchBounds(100,[10,20],15,.5,.01),[0,99]);
});
test('visible endpoint changes ignore fractional borders and gaps',()=>{
 assert.deepEqual(visibleChange([10,20,null,30,60],[.2,3.8]),{delta:10,percent:50});
 assert.equal(visibleChange([null,null],[0,1]),null);
 assert.deepEqual(visibleChange([10,10],[0,1]),{delta:0,percent:0});
});
test('inspection chooses actual daily observations, uses native tie rules and skips missing values',()=>{
 assert.equal(nearestSession([10,20,30],[0,2],.25),0);
 assert.equal(nearestSession([10,null,30],[0,2],.5),0);
 assert.equal(nearestSession([10,20,30],[0,2],.9),2);
 assert.equal(nearestSession([null,null],[0,1],.3),null);
});
test('visible y scale includes overlay values and native 13 percent padding',()=>{
 assert.deepEqual(limits([100,200],[{sma:[50,300]}],[0,1]),[17.5,332.5]);
 assert.equal(limits([null],[],[0,0]),null);
});
test('saved crossings and colours stay attached to each visible line with no duplicate active overlay',()=>{
 const event={index:2,position:1.5,price:20};
 const result={period:2,sma:[null,15,20],events:[event]};
 const saved={id:1,period:2,name:'Recovery',visible:true,sma:result.sma,events:[event],color_hex:'#ff7799'};
 assert.equal(plottedLines({prices:[],lines:[saved],result}).length,1);
 assert.equal(plottedLines({prices:[],lines:[saved],result})[0].events[0].position,1.5);
 assert.equal(plottedLines({prices:[],lines:[{...saved,visible:false}],result}).length,0);
 assert.equal(plottedLines({prices:[],lines:[],result})[0].key,'active');
});
test('web brand sources are the native font/logo files and the restored shared teal',()=>{
 for(const name of ['Manrope-Regular.ttf','Manrope-Bold.ttf'])assert.deepEqual(readFileSync(root+'web/public/fonts/'+name),readFileSync(root+'sma_analyzer/assets/fonts/'+name));
 assert.deepEqual(readFileSync(root+'web/public/app-icon.png'),readFileSync(root+'sma_analyzer/assets/app-icon.png'));
 assert.equal(JSON.parse(readFileSync(root+'sma_analyzer/assets/chart-style.json')).price.dark,'#4DDEC4');
});
test('legacy symbols resolve native bundled logos while unknown identities retain initials',()=>{
 assert.equal(logoUrl({ticker:'VOO'}),'/logos/vanguard.png');
 assert.equal(logoUrl({symbol:'AAPL',logo_url:'https://untrusted.example/logo.png'}),'/logos/apple.png');
 assert.equal(logoUrl({ticker:'UNKNOWN',name:'Unknown fund'}),'');
});
