import {test} from 'node:test';
import assert from 'node:assert/strict';
import {normalizeEmail,submitContact,contactStatus,CONTACT_RECIPIENT,contactCapabilities} from '../lib/contact.js';
import {contactMessage} from '../lib/contact-message.js';
const BODY={email:'volunteer@example.com',install_id:'00000000-0000-4000-8000-000000000001',request_id:'00000000-0000-4000-8000-000000000002',platform:'ios-web',version:'0.17.0'};
function configured(){const names=['RESEND_API_KEY','AUTH_SECRET','SUPABASE_URL','SUPABASE_SECRET_KEY','CONTACT_FROM'],saved=Object.fromEntries(names.map(k=>[k,process.env[k]]));Object.assign(process.env,{RESEND_API_KEY:'re_fixture_no_real_mail',AUTH_SECRET:'fixture-signup-hash-secret',SUPABASE_URL:'https://fixture.supabase.co',SUPABASE_SECRET_KEY:'sb_secret_fixture'});delete process.env.CONTACT_FROM;return ()=>{for(const [k,v]of Object.entries(saved)){if(v===undefined)delete process.env[k];else process.env[k]=v}}}
const row={reference:'fixture-ref',email:'other@example.com',active:true,source:'android',version:'0.17.0',last_action:'modify',changed_at:'2026-11-14T02:30:00Z'};
function event(body={}){const operation=body.p_operation||'save',email=body.p_email||BODY.email,action=operation==='remove'?'remove':body.prior?'modify':'add';return {action,before:body.prior|| (operation==='remove'?email:null),after:operation==='remove'?null:email,email,source:body.p_source||'ios-web',version:body.p_version||'0.17.0',changed_at:row.changed_at,reference:'current-ref',records:[row,{...row,email,source:body.p_source||'ios-web',active:operation!=='remove',last_action:action},{...row,email:'removed@example.com',active:false,last_action:'remove'}]}}
function store(prior){const calls=[],accepted=new Set(),events=new Map(),messages=new Map();return {calls,accepted,events,messages,call:async(name,body)=>{calls.push({name,body});if(name==='sma_prepare_contact'){if(accepted.has(body.p_id))return {action:'accepted',change:events.get(body.p_id).action};if(!events.has(body.p_id))events.set(body.p_id,event({...body,prior}));return {action:'send',event:events.get(body.p_id),message:messages.get(body.p_id)}}if(name==='sma_contact_message'){if(!messages.has(body.p_id))messages.set(body.p_id,body.p_message);return messages.get(body.p_id)}if(name==='sma_finish_contact'){if(body.p_accepted)accepted.add(body.p_id);return true}return {schema_ready:true,protocol:2,signed_up_installations:accepted.size,accepted_submissions:accepted.size}}}}

test('email syntax rejects blank, header injection, multiple recipients and malformed domains',()=>{
 for(const email of ['', 'no-at', 'x@example.com\nBcc: other@example.com','x@example.com,y@example.com','x@localhost','x@.com','x@example..com'])assert.throws(()=>normalizeEmail(email));
 assert.equal(normalizeEmail(' volunteer@example.com '),'volunteer@example.com');
});
test('unconfigured signup stays disabled and sends nothing',async()=>{
 const key=process.env.RESEND_API_KEY;delete process.env.RESEND_API_KEY;
 try{assert.deepEqual(await contactCapabilities(),{enabled:false});assert.equal((await submitContact(BODY,{send:()=>{throw new Error('No email')}})).status,503)}finally{if(key!==undefined)process.env.RESEND_API_KEY=key}
});
test('fixed-recipient email includes source, version and private active/removed summary',async()=>{
 const restore=configured(),db=store();let sends=0;
 try{
  const send=async(url,options)=>{sends++;assert.equal(url,'https://api.resend.com/emails');const value=JSON.parse(options.body);assert.deepEqual(value.to,[CONTACT_RECIPIENT]);assert.equal(value.reply_to,BODY.email);assert.equal(value.from,'SMA Stock Analyzer <onboarding@resend.dev>');assert.ok(value.text.includes('Source: iOS web app'));assert.ok(value.text.includes('App version: 0.17.0'));assert.ok(value.text.includes('EXISTING USERS (2)'));assert.ok(value.text.includes('REMOVED EMAILS (1)'));assert.ok(value.text.includes('removed@example.com'));assert.ok(value.html.includes('<table'));return Response.json({id:'fixture-mail'})};
  const result=await submitContact({...BODY,to:'attacker@example.com'},{ip:'192.0.2.1',call:db.call,send});assert.equal(result.payload.sent,true);assert.ok(!JSON.stringify(result).includes('other@example.com'));
  assert.equal((await submitContact(BODY,{call:db.call,send})).payload.already_accepted,true);assert.equal(sends,1);
  const claim=db.calls.find(x=>x.name==='sma_prepare_contact').body;assert.ok(!JSON.stringify(claim).includes(BODY.install_id));assert.ok(!JSON.stringify(claim).includes('192.0.2.1'));assert.equal(claim.p_source,'ios-web');
 }finally{restore()}
});
test('modification email shows old and new addresses and modify action',async()=>{
 const restore=configured(),db=store('previous@example.com');let mail;
 try{const result=await submitContact(BODY,{call:db.call,send:async(_,o)=>{mail=JSON.parse(o.body);return Response.json({id:'fixture-modify'})}});assert.equal(result.payload.change,'modify');assert.ok(mail.text.includes('Previous email: previous@example.com'));assert.ok(mail.text.includes('Current email: volunteer@example.com'));assert.ok(mail.subject.endsWith('email modify'))}finally{restore()}
});
test('removal is explicit and emails the owner, never the removed address',async()=>{
 const restore=configured(),db=store();let mail;
 try{const result=await submitContact({...BODY,operation:'remove',platform:'android'},{call:db.call,send:async(_,o)=>{mail=JSON.parse(o.body);return Response.json({id:'fixture-remove'})}});assert.equal(result.payload.change,'remove');assert.deepEqual(mail.to,[CONTACT_RECIPIENT]);assert.ok(mail.text.includes('Last change: remove'));assert.ok(mail.text.includes('Current email: None'));assert.ok(mail.text.includes('Source: Android APK'));assert.ok(mail.text.includes('REMOVED EMAILS (2)'))}finally{restore()}
});
test('uncertain retries freeze source/version, summary, sender and full payload across deployments',async()=>{
 const restore=configured(),db=store(),payloads=[];
 try{const send=async(_,o)=>{payloads.push(o);if(payloads.length===1)throw new Error('fixture timeout');return Response.json({id:'fixture-mail'})};assert.equal((await submitContact(BODY,{call:db.call,send})).status,503);process.env.CONTACT_FROM='New sender <updates@example.com>';assert.equal((await submitContact({...BODY,platform:'android',version:'9.0'},{call:db.call,send})).status,200);assert.equal(payloads[0].body,payloads[1].body);assert.equal(payloads[0].headers['Idempotency-Key'],payloads[1].headers['Idempotency-Key'])}finally{restore()}
});
test('provider acceptance without durable commit stays retryable and does not claim completion',async()=>{
 const restore=configured(),db=store();let fail=true;
 try{const call=async(n,b)=>{if(n==='sma_finish_contact'&&b.p_accepted&&fail)throw new Error('fixture storage outage');return db.call(n,b)};const send=async()=>Response.json({id:'same-idempotent-message'});assert.equal((await submitContact(BODY,{call,send})).status,503);assert.equal(db.accepted.size,0);fail=false;assert.equal((await submitContact(BODY,{call,send})).status,200)}finally{restore()}
});
test('same-address and repeated-removal no-ops send nothing',async()=>{
 const restore=configured();try{const result=await submitContact(BODY,{call:async()=>({action:'unchanged',change:'add'}),send:()=>{throw new Error('No email')}});assert.equal(result.payload.unchanged,true)}finally{restore()}
});
test('limits, concurrent/stale changes and expired intents never call the provider',async()=>{
 const restore=configured();try{for(const [action,status]of [['busy',429],['rate_limited',429],['attempt_limit',429],['expired',410],['conflict',400],['pending_change',409],['stale',409]]){const result=await submitContact(BODY,{call:async()=>({action}),send:()=>{throw new Error('No email')}});assert.equal(result.status,status);if(action==='expired')assert.equal(result.payload.code,'expired')}}finally{restore()}
});
test('provider failures do not claim success or expose private diagnostic bodies',async()=>{
 const restore=configured(),db=store();try{const result=await submitContact(BODY,{call:db.call,send:async()=>Response.json({message:'re_sensitive_fixture'},{status:403})});assert.equal(result.status,503);assert.ok(!JSON.stringify(result).includes('re_sensitive'));assert.equal(db.accepted.size,0)}finally{restore()}
});
test('ambiguous provider errors and malformed successes remain pending for the same intent',async()=>{
 const restore=configured();try{for(const status of [200,409,500]){const db=store();const result=await submitContact(BODY,{call:db.call,send:async()=>Response.json({message:'fixture uncertainty'},{status})});assert.equal(result.status,503);assert.equal(db.calls.filter(x=>x.name==='sma_finish_contact').length,0)}}finally{restore()}
});
test('legacy hash-only schema requires migration and status never exposes email lists',async()=>{
 const restore=configured();try{const old=await contactStatus(async()=>({schema_ready:true}));assert.equal(old.ready,false);const status=await contactStatus(async()=>({schema_ready:true,protocol:2,signed_up_installations:3,accepted_submissions:5,active_entries:2,removed_entries:1}));assert.equal(status.ready,true);assert.ok(!JSON.stringify(status).includes(process.env.RESEND_API_KEY));assert.equal(status.active_entries,2)}finally{restore()}
});
test('HTML template escapes addresses and shows removal action/source/date per row',()=>{
 const detail=event({p_operation:'remove'});detail.records[0].email='unsafe<&@example.com';const message=contactMessage(detail,{from:'sender@example.com',to:CONTACT_RECIPIENT});assert.ok(message.html.includes('unsafe&lt;&amp;@example.com'));assert.ok(!message.html.includes('unsafe<&'));assert.ok(message.text.includes('SGT'));assert.ok(message.text.includes('modify'));assert.ok(message.text.includes('remove'));
});
