-- Optional release updates, protocol 2. Private addresses/history support owner summaries.
-- Rerun in Supabase SQL Editor to upgrade; retains existing records and notification jobs.
begin;
create table if not exists public.sma_contact_submissions (
 id text primary key check(length(id)=64),
 install_hash text not null check(length(install_hash)=64),
 email_hash text not null check(length(email_hash)=64),
 state text not null default 'pending' check(state in ('pending','accepted','failed')),
 created_at timestamptz not null default now(),
 attempted_at timestamptz not null default now(),
 accepted_at timestamptz,
 attempts integer not null default 1,
 provider_id text,
 error_code integer
);
create table if not exists public.sma_contact_installations (
 install_hash text primary key, first_signup_at timestamptz not null default now()
);
create table if not exists public.sma_contact_limits (
 bucket text primary key, hits integer not null default 0, expires_at timestamptz not null
);
alter table public.sma_contact_submissions enable row level security;
alter table public.sma_contact_installations enable row level security;
alter table public.sma_contact_limits enable row level security;
revoke all on public.sma_contact_submissions,public.sma_contact_installations,public.sma_contact_limits from public,anon,authenticated;
grant all on public.sma_contact_submissions,public.sma_contact_installations,public.sma_contact_limits to service_role;

create or replace function public.sma_claim_contact(p_id text,p_install_hash text,p_email_hash text,p_ip_hash text)
returns jsonb language plpgsql security invoker set search_path=public as $$
declare previous sma_contact_submissions%rowtype;
 keys text[]; quotas integer[]:=array[20,80,2000,5,5];
 spans integer[]:=array[3600,86400,2678400,3600,3600];
 epoch bigint:=floor(extract(epoch from now())); current_hits integer; n integer;
begin
 if length(p_id)<>64 or length(p_install_hash)<>64 or length(p_email_hash)<>64 or length(p_ip_hash)<>64 then
  return jsonb_build_object('action','invalid');
 end if;
 perform pg_advisory_xact_lock(hashtextextended('sma_contact_delivery',0));
 select * into previous from sma_contact_submissions where id=p_id for update;
 if found then
  if previous.install_hash<>p_install_hash or previous.email_hash<>p_email_hash then return jsonb_build_object('action','conflict'); end if;
  if previous.state='accepted' then return jsonb_build_object('action','accepted'); end if;
  if previous.created_at < now()-interval '23 hours' then return jsonb_build_object('action','expired'); end if;
  if previous.state='pending' and previous.attempted_at > now()-interval '45 seconds' then return jsonb_build_object('action','busy'); end if;
  if previous.attempts>=4 then return jsonb_build_object('action','attempt_limit'); end if;
 end if;
 delete from sma_contact_limits where expires_at<now();
 keys:=array['hour:'||(epoch/3600),'day:'||(epoch/86400),
             'month:'||to_char(now() at time zone 'UTC','YYYYMM'),
             'install:'||p_install_hash||':'||(epoch/3600),
             'ip:'||p_ip_hash||':'||(epoch/3600)];
 for n in 1..array_length(keys,1) loop
  select hits into current_hits from sma_contact_limits where bucket=keys[n];
  if coalesce(current_hits,0)>=quotas[n] then return jsonb_build_object('action','rate_limited'); end if;
 end loop;
 for n in 1..array_length(keys,1) loop
  insert into sma_contact_limits(bucket,hits,expires_at) values(keys[n],1,now()+make_interval(secs=>spans[n]))
   on conflict(bucket) do update set hits=sma_contact_limits.hits+1;
 end loop;
 insert into sma_contact_submissions(id,install_hash,email_hash) values(p_id,p_install_hash,p_email_hash)
  on conflict(id) do update set state='pending',attempted_at=now(),attempts=sma_contact_submissions.attempts+1,error_code=null;
 return jsonb_build_object('action','send','new_signup',not exists(select 1 from sma_contact_installations where install_hash=p_install_hash));
end; $$;

create or replace function public.sma_finish_contact(p_id text,p_accepted boolean,p_provider_id text default null,p_error_code integer default null)
returns boolean language plpgsql security invoker set search_path=public as $$
declare installation text;
begin
 update sma_contact_submissions set state=case when p_accepted then 'accepted' else 'failed' end,
 accepted_at=case when p_accepted then now() else null end,provider_id=p_provider_id,error_code=p_error_code
 where id=p_id and state<>'accepted' returning install_hash into installation;
 if p_accepted and installation is not null then
  insert into sma_contact_installations(install_hash) values(installation) on conflict do nothing;
 end if;
 return installation is not null;
end; $$;
create or replace function public.sma_contact_status()
returns jsonb language sql security invoker set search_path=public as $$
 select jsonb_build_object('schema_ready',true,
 'signed_up_installations',(select count(*) from sma_contact_installations),
 'accepted_submissions',(select count(*) from sma_contact_submissions where state='accepted'));
$$;
revoke all on function public.sma_claim_contact(text,text,text,text),public.sma_finish_contact(text,boolean,text,integer),public.sma_contact_status() from public,anon,authenticated;
grant execute on function public.sma_claim_contact(text,text,text,text),public.sma_finish_contact(text,boolean,text,integer),public.sma_contact_status() to service_role;
-- Upgrade the original hash-only journal without inventing missing email addresses.
alter table public.sma_contact_submissions add column if not exists operation text;
alter table public.sma_contact_submissions add column if not exists event jsonb;
alter table public.sma_contact_submissions add column if not exists message jsonb;
alter table public.sma_contact_installations add column if not exists contact_revision bigint not null default 0;
create table if not exists public.sma_contact_addresses (
 install_hash text not null,
 email_hash text not null,
 email text not null check(length(email) between 3 and 254),
 active boolean not null,
 source text not null,
 app_version text not null,
 last_action text not null check(last_action in ('add','modify','remove')),
 changed_at timestamptz not null,
 primary key(install_hash,email_hash)
);
create unique index if not exists sma_contact_one_active on public.sma_contact_addresses(install_hash) where active;
alter table public.sma_contact_addresses enable row level security;
revoke all on public.sma_contact_addresses from public,anon,authenticated;
grant all on public.sma_contact_addresses to service_role;

create or replace function public.sma_prepare_contact(
 p_id text,p_install_hash text,p_email_hash text,p_ip_hash text,
 p_email text,p_operation text,p_source text,p_version text)
returns jsonb language plpgsql security invoker set search_path=public as $$
declare previous sma_contact_submissions%rowtype; current_address sma_contact_addresses%rowtype;
 result jsonb; detail jsonb; summary jsonb; change_kind text; before_email text;
 revision bigint; changed timestamptz:=clock_timestamp();
begin
 if p_operation not in ('save','remove') or p_email is null or length(p_email) not between 3 and 254
 or p_source not in ('android','ios-web','web','unknown') or length(p_version)>40 then
  return jsonb_build_object('action','invalid');
 end if;
 perform pg_advisory_xact_lock(hashtextextended('sma_contact_delivery',0));
 -- Full roster copies are only needed during Resend's retry window. Keep the
 -- registry and per-change details, but discard expired bulk snapshots on activity.
 update sma_contact_submissions set event=event-'records',message=null
 where created_at<now()-interval '24 hours' and (event?'records' or message is not null);
 select * into previous from sma_contact_submissions where id=p_id;
 if found then
  if previous.install_hash<>p_install_hash or previous.email_hash<>p_email_hash
  or (previous.operation is not null and previous.operation<>p_operation) then
   return jsonb_build_object('action','conflict');
  end if;
  if previous.state='accepted' then
   if previous.event is null then return jsonb_build_object('action','expired'); end if;
   return jsonb_build_object('action','accepted','change',previous.event->>'action');
  end if;
 end if;
 select coalesce((select contact_revision from sma_contact_installations where install_hash=p_install_hash),0) into revision;
 if previous.event is not null and (previous.event->>'base_revision')::bigint<>revision then
  return jsonb_build_object('action','expired');
 end if;
 -- An uncertain earlier delivery must be retried before another change on this installation.
 if exists(select 1 from sma_contact_submissions where install_hash=p_install_hash and id<>p_id
  and event is not null and state='pending' and created_at>now()-interval '23 hours') then
  return jsonb_build_object('action','pending_change');
 end if;
 select * into current_address from sma_contact_addresses where install_hash=p_install_hash and active;
 if previous.event is null then
  if p_operation='save' and current_address.email_hash=p_email_hash then
   return jsonb_build_object('action','unchanged','change','add');
  end if;
  if p_operation='remove' then
   if current_address.email is not null and current_address.email_hash<>p_email_hash then
    return jsonb_build_object('action','stale');
   end if;
   if current_address.email is null and exists(select 1 from sma_contact_addresses where install_hash=p_install_hash and email_hash=p_email_hash and not active) then
    return jsonb_build_object('action','unchanged','change','remove');
   end if;
  end if;
 end if;
 result:=sma_claim_contact(p_id,p_install_hash,p_email_hash,p_ip_hash);
 if result->>'action'<>'send' then return result; end if;
 if previous.event is not null then
  return jsonb_build_object('action','send','event',previous.event,'message',previous.message);
 end if;
 change_kind:=case when p_operation='remove' then 'remove' when current_address.email is null then 'add' else 'modify' end;
 before_email:=coalesce(current_address.email,case when p_operation='remove' then p_email else null end);
 -- A stable snapshot includes this proposed change and all previously accepted changes.
 with projected as (
  select a.install_hash,a.email,
   case when a.install_hash=p_install_hash and a.active then false else a.active end as active,
   case when a.install_hash=p_install_hash and a.active then p_source else a.source end as source,
   case when a.install_hash=p_install_hash and a.active then p_version else a.app_version end as app_version,
   case when a.install_hash=p_install_hash and a.active then change_kind else a.last_action end as last_action,
   case when a.install_hash=p_install_hash and a.active then changed else a.changed_at end as changed_at
  from sma_contact_addresses a where not(a.install_hash=p_install_hash and a.email_hash=p_email_hash)
  union all
  select p_install_hash,p_email,p_operation='save',p_source,p_version,change_kind,changed
 ) select coalesce(jsonb_agg(jsonb_build_object('reference',left(install_hash,12),'email',email,'active',active,
  'source',source,'version',app_version,'last_action',last_action,'changed_at',changed_at)
  order by lower(email),install_hash),'[]'::jsonb) into summary from projected;
 detail:=jsonb_build_object('action',change_kind,'before',before_email,
  'after',case when p_operation='save' then p_email else null end,'email',p_email,
  'source',p_source,'version',p_version,'changed_at',changed,'reference',left(p_install_hash,12),
  'base_revision',revision,'records',summary,
  'legacy_accepted',(select count(*) from sma_contact_submissions where state='accepted' and event is null));
 update sma_contact_submissions set operation=p_operation,event=detail where id=p_id;
 return jsonb_build_object('action','send','event',detail,'message',null);
end; $$;

-- Freeze the complete provider payload, including template/sender, across retries/deploys.
create or replace function public.sma_contact_message(p_id text,p_message jsonb)
returns jsonb language plpgsql security invoker set search_path=public as $$
declare payload jsonb;
begin
 update sma_contact_submissions set message=coalesce(message,p_message)
 where id=p_id and event is not null returning message into payload;
 if payload is null then raise exception 'Contact request unavailable'; end if;
 return payload;
end; $$;

create or replace function public.sma_finish_contact(p_id text,p_accepted boolean,p_provider_id text default null,p_error_code integer default null)
returns boolean language plpgsql security invoker set search_path=public as $$
declare submission sma_contact_submissions%rowtype; detail jsonb; revision bigint;
begin
 perform pg_advisory_xact_lock(hashtextextended('sma_contact_delivery',0));
 select * into submission from sma_contact_submissions where id=p_id for update;
 if not found then return false; end if;
 if submission.state='accepted' then return true; end if;
 detail:=submission.event;
 if p_accepted then
  insert into sma_contact_installations(install_hash) values(submission.install_hash) on conflict do nothing;
  if detail is not null then
   select contact_revision into revision from sma_contact_installations where install_hash=submission.install_hash;
   if revision<>(detail->>'base_revision')::bigint then raise exception 'Contact revision changed'; end if;
   update sma_contact_addresses set active=false,last_action=detail->>'action',source=detail->>'source',
    app_version=detail->>'version',changed_at=(detail->>'changed_at')::timestamptz
    where install_hash=submission.install_hash and active;
   insert into sma_contact_addresses(install_hash,email_hash,email,active,source,app_version,last_action,changed_at)
    values(submission.install_hash,submission.email_hash,detail->>'email',submission.operation='save',
     detail->>'source',detail->>'version',detail->>'action',(detail->>'changed_at')::timestamptz)
    on conflict(install_hash,email_hash) do update set email=excluded.email,active=excluded.active,
     source=excluded.source,app_version=excluded.app_version,last_action=excluded.last_action,changed_at=excluded.changed_at;
   update sma_contact_installations set contact_revision=contact_revision+1 where install_hash=submission.install_hash;
  end if;
 end if;
 update sma_contact_submissions set state=case when p_accepted then 'accepted' else 'failed' end,
  accepted_at=case when p_accepted then now() else null end,provider_id=p_provider_id,error_code=p_error_code where id=p_id;
 return true;
end; $$;

create or replace function public.sma_contact_status()
returns jsonb language sql security invoker set search_path=public as $$
 select jsonb_build_object('schema_ready',true,'protocol',2,
 'signed_up_installations',(select count(*) from sma_contact_installations),
 'accepted_submissions',(select count(*) from sma_contact_submissions where state='accepted'),
 'active_entries',(select count(*) from sma_contact_addresses where active),
 'removed_entries',(select count(*) from sma_contact_addresses where not active),
 'legacy_accepted',(select count(*) from sma_contact_submissions where state='accepted' and event is null));
$$;
revoke all on function public.sma_prepare_contact(text,text,text,text,text,text,text,text),public.sma_contact_message(text,jsonb) from public,anon,authenticated;
grant execute on function public.sma_prepare_contact(text,text,text,text,text,text,text,text),public.sma_contact_message(text,jsonb) to service_role;
commit;
select public.sma_contact_status();
