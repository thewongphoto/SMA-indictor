-- Run in your own Supabase project's SQL Editor after adding the Vercel variables.
-- Idempotent: preserves subscriptions, saved alert choices and delivery history.
create extension if not exists pg_cron;
create extension if not exists pgcrypto with schema extensions;
create extension if not exists pg_net with schema extensions;
create extension if not exists supabase_vault with schema vault;

create table if not exists public.sma_push_devices (
 id uuid primary key,
 subscription jsonb not null,
 lines jsonb not null default '[]'::jsonb check (jsonb_typeof(lines)='array' and jsonb_array_length(lines)<=100),
 settings jsonb not null default '{}'::jsonb,
 revision bigint not null check (revision>=0),
 enabled boolean not null default true,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create table if not exists public.sma_alert_history (
 counter text primary key, data jsonb not null, fetched_at timestamptz not null default now()
);
create table if not exists public.sma_alert_runs (
 job text not null check (job in ('US','SG','US_START','SG_START')),
 due timestamptz not null, started_at timestamptz not null default now(),
 finished_at timestamptz, status text not null default 'started',
 checked integer not null default 0, posted integer not null default 0,
 primary key(job,due)
);
create table if not exists public.sma_alert_events (
 key text primary key, device_id uuid not null references public.sma_push_devices(id) on delete cascade,
 created_at timestamptz not null default now(), status text not null default 'claimed', code integer
);
alter table public.sma_push_devices enable row level security;
alter table public.sma_alert_history enable row level security;
alter table public.sma_alert_runs enable row level security;
alter table public.sma_alert_events enable row level security;
revoke all on public.sma_push_devices,public.sma_alert_history,public.sma_alert_runs,public.sma_alert_events from anon,authenticated;
grant all on public.sma_push_devices,public.sma_alert_history,public.sma_alert_runs,public.sma_alert_events to service_role;

create or replace function public.sma_sync_device(p_id uuid,p_subscription jsonb,p_lines jsonb,p_settings jsonb,p_revision bigint)
returns boolean language plpgsql security invoker set search_path=public as $$
declare changed boolean;
begin
 insert into sma_push_devices as d (id,subscription,lines,settings,revision)
 values (p_id,p_subscription,p_lines,p_settings,p_revision)
 on conflict (id) do update set subscription=excluded.subscription,lines=excluded.lines,settings=excluded.settings,
 revision=excluded.revision,enabled=true,updated_at=now() where excluded.revision>=d.revision
 returning true into changed;
 return coalesce(changed,false);
end; $$;
create or replace function public.sma_claim_run(p_job text,p_due timestamptz)
returns boolean language plpgsql security invoker set search_path=public as $$
declare claimed boolean;
begin
 insert into sma_alert_runs(job,due) values(p_job,p_due) on conflict do nothing returning true into claimed;
 return coalesce(claimed,false);
end; $$;
create or replace function public.sma_claim_event(p_key text,p_device uuid)
returns boolean language plpgsql security invoker set search_path=public as $$
declare claimed boolean;
begin
 insert into sma_alert_events(key,device_id) values(p_key,p_device) on conflict do nothing returning true into claimed;
 return coalesce(claimed,false);
end; $$;
revoke all on function public.sma_sync_device(uuid,jsonb,jsonb,jsonb,bigint),public.sma_claim_run(text,timestamptz),public.sma_claim_event(text,uuid) from public,anon,authenticated;
grant execute on function public.sma_sync_device(uuid,jsonb,jsonb,jsonb,bigint),public.sma_claim_run(text,timestamptz),public.sma_claim_event(text,uuid) to service_role;

-- Values below are filled by the private /setup page. Never commit the filled SQL.
do $$
declare secret_id uuid;
begin
 select id into secret_id from vault.secrets where name='sma_app_url' limit 1;
 if secret_id is null then perform vault.create_secret('__APP_URL__','sma_app_url');
 else perform vault.update_secret(secret_id,'__APP_URL__'); end if;
 select id into secret_id from vault.secrets where name='sma_cron_secret' limit 1;
 if secret_id is null then perform vault.create_secret('__CRON_SECRET__','sma_cron_secret');
 else perform vault.update_secret(secret_id,'__CRON_SECRET__'); end if;
end; $$;

-- pg_cron uses UTC. Four fixed Singapore-time targets, with weekday rules shared with Android.
select cron.schedule('sma-us-close','30 22 * * 1-5',$job$
 select net.http_post(url:=(select decrypted_secret from vault.decrypted_secrets where name='sma_app_url')||'/api/push/check?job=US',
 headers:=jsonb_build_object('Content-Type','application/json','Authorization','Bearer '||(select decrypted_secret from vault.decrypted_secrets where name='sma_cron_secret')),body:='{}'::jsonb,timeout_milliseconds:=60000); $job$);
select cron.schedule('sma-sg-close','30 10 * * 1-5',$job$
 select net.http_post(url:=(select decrypted_secret from vault.decrypted_secrets where name='sma_app_url')||'/api/push/check?job=SG',
 headers:=jsonb_build_object('Content-Type','application/json','Authorization','Bearer '||(select decrypted_secret from vault.decrypted_secrets where name='sma_cron_secret')),body:='{}'::jsonb,timeout_milliseconds:=60000); $job$);
select cron.schedule('sma-us-open','30 13 * * 1-5',$job$
 select net.http_post(url:=(select decrypted_secret from vault.decrypted_secrets where name='sma_app_url')||'/api/push/check?job=US_START',
 headers:=jsonb_build_object('Content-Type','application/json','Authorization','Bearer '||(select decrypted_secret from vault.decrypted_secrets where name='sma_cron_secret')),body:='{}'::jsonb,timeout_milliseconds:=60000); $job$);
select cron.schedule('sma-sg-open','0 1 * * 1-5',$job$
 select net.http_post(url:=(select decrypted_secret from vault.decrypted_secrets where name='sma_app_url')||'/api/push/check?job=SG_START',
 headers:=jsonb_build_object('Content-Type','application/json','Authorization','Bearer '||(select decrypted_secret from vault.decrypted_secrets where name='sma_cron_secret')),body:='{}'::jsonb,timeout_milliseconds:=60000); $job$);

create or replace function public.sma_setup_status()
returns jsonb language sql security definer set search_path=public as $$
 select jsonb_build_object('schema_ready',true,'scheduled_jobs',
 (select count(*) from cron.job where jobname in ('sma-us-close','sma-sg-close','sma-us-open','sma-sg-open') and active),
 'app_url',(select decrypted_secret from vault.decrypted_secrets where name='sma_app_url' limit 1),
 'cron_secret_sha256',(select encode(extensions.digest(decrypted_secret,'sha256'),'hex') from vault.decrypted_secrets where name='sma_cron_secret' limit 1));
$$;
revoke all on function public.sma_setup_status() from public,anon,authenticated;
grant execute on function public.sma_setup_status() to service_role;
select public.sma_setup_status();
