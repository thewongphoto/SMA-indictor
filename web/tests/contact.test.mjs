import {test} from 'node:test';
import assert from 'node:assert/strict';
import {normalizeEmail,submitContact,contactStatus,CONTACT_RECIPIENT,contactCapabilities} from '../lib/contact.js';
const BODY={email:'volunteer@example.com',install_id:'00000000-0000-4000-8000-000000000001',request_id:'00000000-0000-4000-8000-000000000002',platform:'ios-web',version:'0.16.0'};
function configured(){const names=['RESEND_API_KEY','AUTH_SECRET','SUPABASE_URL','SUPABASE_SECRET_KEY','CONTACT_FROM'],saved=Object.fromEntries(names.map(k=>[k,process.env[k]]));Object.assign(process.env,{RESEND_API_KEY:'re_fixture_no_real_mail',AUTH_SECRET:'fixture-signup-hash-secret',SUPABASE_URL:'https://fixture.supabase.co',SUPABASE_SECRET_KEY:'sb_secret_fixture'});delete process.env.CONTACT_FROM;return ()=>{for(const [k,v]of Object.entries(saved)){if(v===undefined)delete process.env[k];else process.env[k]=v}}}
function store(){const calls=[],accepted=new Set();return {calls,accepted,call:async(name,body)=>{calls.push({name,body});if(name==='sma_claim_contact')return {action:accepted.has(body.p_id)?'accepted':'send',new_signup:true};if(name==='sma_finish_contact'){if(body.p_accepted)accepted.add(body.p_id);return true}return {schema_ready:true,signed_up_installations:accepted.size,accepted_submissions:accepted.size}}}}

test('email syntax rejects blank, header injection, multiple recipients and malformed domains',()=>{
 for(const email of ['', 'no-at', 'x@example.com\nBcc: other@example.com','x@example.com,y@example.com','x@localhost','x@.com','x@example..com'])assert.throws(()=>normalizeEmail(email));
 assert.equal(normalizeEmail(' volunteer@example.com '),'volunteer@example.com');
});
test('unconfigured signup stays disabled and sends nothing',async()=>{
 const key=process.env.RESEND_API_KEY;delete process.env.RESEND_API_KEY;
 try{assert.deepEqual(await contactCapabilities(),{enabled:false});const result=await submitContact(BODY,{send:()=>{throw new Error('No email should be sent')}});assert.equal(result.status,503)}finally{if(key!==undefined)process.env.RESEND_API_KEY=key}
});
test('configured signup forwards only to the fixed owner and repeated accepted requests send once',async()=>{
 const restore=configured(),db=store();let sends=0;
 try{
  const send=async(url,options)=>{sends++;assert.equal(url,'https://api.resend.com/emails');const value=JSON.parse(options.body);assert.deepEqual(value.to,[CONTACT_RECIPIENT]);assert.equal(value.reply_to,BODY.email);assert.equal(value.from,'SMA Stock Analyzer <onboarding@resend.dev>');assert.ok(value.text.includes(BODY.email));assert.ok(options.headers['Idempotency-Key'].startsWith('sma-contact/'));return Response.json({id:'fixture-mail'})};
  const body={...BODY,to:'attacker@example.com'};
  assert.equal((await submitContact(body,{call:db.call,send})).payload.sent,true);
  assert.equal((await submitContact(body,{call:db.call,send})).payload.already_accepted,true);
  assert.equal(sends,1);
  const claim=db.calls.find(x=>x.name==='sma_claim_contact').body;assert.ok(!JSON.stringify(claim).includes(BODY.email));assert.ok(!JSON.stringify(claim).includes(BODY.install_id));
 }finally{restore()}
});
test('changed addresses use a new intent and send a new email',async()=>{
 const restore=configured(),db=store();let sends=0;
 try{const send=async()=>{sends++;return Response.json({id:'fixture-'+sends})};await submitContact(BODY,{call:db.call,send});await submitContact({...BODY,email:'changed@example.com',request_id:'00000000-0000-4000-8000-000000000003'},{call:db.call,send});assert.equal(sends,2);assert.equal(db.accepted.size,2)}finally{restore()}
});
test('uncertain network acceptance retains the same provider idempotency key and payload',async()=>{
 const restore=configured(),db=store(),payloads=[];
 try{
  const send=async(url,options)=>{payloads.push(options);if(payloads.length===1)throw new Error('fixture timeout');return Response.json({id:'fixture-mail'})};
  const first=await submitContact(BODY,{call:db.call,send});assert.equal(first.status,503);assert.equal(db.calls.filter(x=>x.name==='sma_finish_contact').length,0);
  const second=await submitContact({...BODY,platform:'android',version:'0.17.0'},{call:db.call,send});assert.equal(second.status,200);
  assert.equal(payloads[0].headers['Idempotency-Key'],payloads[1].headers['Idempotency-Key']);assert.equal(payloads[0].body,payloads[1].body);
 }finally{restore()}
});
test('rate limits, concurrent claims and expired intents never call the email provider',async()=>{
 const restore=configured();
 try{for(const [action,status]of [['busy',429],['rate_limited',429],['attempt_limit',429],['expired',410],['conflict',400]]){const result=await submitContact(BODY,{call:async()=>({action}),send:()=>{throw new Error('No email should be sent')}});assert.equal(result.status,status);if(action==='expired')assert.equal(result.payload.code,'expired')}}finally{restore()}
});
test('provider failures do not claim success or expose its private response body',async()=>{
 const restore=configured(),db=store();
 try{const result=await submitContact(BODY,{call:db.call,send:async()=>Response.json({message:'private provider diagnostic re_sensitive_fixture'},{status:403})});assert.equal(result.status,503);assert.equal(result.payload.sent,undefined);assert.ok(!JSON.stringify(result).includes('re_sensitive'));assert.equal(db.accepted.size,0)}finally{restore()}
});
test('readiness reports configuration and anonymous counts without sending mail',async()=>{
 const restore=configured();
 try{const status=await contactStatus(async()=>({schema_ready:true,signed_up_installations:3,accepted_submissions:5}));assert.equal(status.ready,true);assert.equal(status.recipient,'kelwong98@gmail.com');assert.equal(status.signed_up_installations,3);assert.ok(!JSON.stringify(status).includes(process.env.RESEND_API_KEY))}finally{restore()}
});
