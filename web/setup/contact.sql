-- Optional release-update signup. No email addresses or raw IPs are stored here.
-- Run once in the same Supabase SQL Editor; safe to rerun without deleting records.
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
select public.sma_contact_status();
