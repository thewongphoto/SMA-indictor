-- Run against an isolated database after setup/contact.sql, never production.
set role anon;
do $$ begin
 begin perform public.sma_contact_status(); raise exception 'Anonymous RPC access was allowed';
 exception when insufficient_privilege then null; end;
 begin perform count(*) from public.sma_contact_submissions; raise exception 'Anonymous table access was allowed';
 exception when insufficient_privilege then null; end;
end $$;
reset role;
set role service_role;
do $$
declare result jsonb; n integer; id text;
begin
 result:=sma_claim_contact(repeat('a',64),repeat('b',64),repeat('c',64),repeat('d',64));
 if result->>'action'<>'send' then raise exception 'Initial submission rejected: %',result; end if;
 if sma_claim_contact(repeat('a',64),repeat('b',64),repeat('c',64),repeat('d',64))->>'action'<>'busy' then raise exception 'Concurrent claim not blocked'; end if;
 if sma_claim_contact(repeat('a',64),repeat('b',64),repeat('e',64),repeat('d',64))->>'action'<>'conflict' then raise exception 'Changed payload not rejected'; end if;
 perform sma_finish_contact(repeat('a',64),true,'fixture-provider');
 if sma_claim_contact(repeat('a',64),repeat('b',64),repeat('c',64),repeat('d',64))->>'action'<>'accepted' then raise exception 'Accepted retry was not deduplicated'; end if;
 perform sma_claim_contact(repeat('f',64),repeat('b',64),repeat('e',64),repeat('d',64));
 perform sma_finish_contact(repeat('f',64),true,'fixture-change');
 result:=sma_contact_status();
 if (result->>'signed_up_installations')::integer<>1 or (result->>'accepted_submissions')::integer<>2 then raise exception 'Address changes inflated consent count: %',result; end if;
 -- Repeated failed attempts have a finite retry budget.
 perform sma_claim_contact(repeat('e',64),repeat('c',64),repeat('d',64),repeat('a',64));
 for n in 1..3 loop
  perform sma_finish_contact(repeat('e',64),false,null,503);
  result:=sma_claim_contact(repeat('e',64),repeat('c',64),repeat('d',64),repeat('a',64));
  if result->>'action'<>'send' then raise exception 'Retry unexpectedly rejected'; end if;
 end loop;
 perform sma_finish_contact(repeat('e',64),false,null,503);
 if sma_claim_contact(repeat('e',64),repeat('c',64),repeat('d',64),repeat('a',64))->>'action'<>'attempt_limit' then raise exception 'Retry budget not enforced'; end if;
 update sma_contact_submissions set created_at=now()-interval '24 hours' where sma_contact_submissions.id=repeat('e',64);
 if sma_claim_contact(repeat('e',64),repeat('c',64),repeat('d',64),repeat('a',64))->>'action'<>'expired' then raise exception 'Expired provider idempotency window was reused'; end if;
 truncate sma_contact_submissions,sma_contact_limits,sma_contact_installations;
 -- Five per-IP requests are accepted; a sixth distinct installation is blocked.
 for n in 1..5 loop
  id:=repeat(md5(n::text),2);
  result:=sma_claim_contact(id,id,id,repeat('a',64));
  if result->>'action'<>'send' then raise exception 'IP quota applied too early'; end if;
 end loop;
 if sma_claim_contact(repeat('b',64),repeat('b',64),repeat('b',64),repeat('a',64))->>'action'<>'rate_limited' then raise exception 'IP quota not enforced'; end if;
 truncate sma_contact_submissions,sma_contact_limits,sma_contact_installations;
 -- Five per-installation requests are accepted even across different IPs.
 for n in 1..5 loop
  id:=repeat(md5(n::text),2);
  result:=sma_claim_contact(id,repeat('a',64),id,id);
  if result->>'action'<>'send' then raise exception 'Installation quota applied too early'; end if;
 end loop;
 if sma_claim_contact(repeat('b',64),repeat('a',64),repeat('b',64),repeat('b',64))->>'action'<>'rate_limited' then raise exception 'Installation quota not enforced'; end if;
 truncate sma_contact_submissions,sma_contact_limits,sma_contact_installations;
 -- Independent installations/IPs still share the owner's hourly cap.
 for n in 1..20 loop
  id:=repeat(md5(n::text),2);
  result:=sma_claim_contact(id,id,id,id);
  if result->>'action'<>'send' then raise exception 'Global quota applied too early'; end if;
 end loop;
 if sma_claim_contact(repeat('b',64),repeat('b',64),repeat('b',64),repeat('b',64))->>'action'<>'rate_limited' then raise exception 'Global quota not enforced'; end if;
 truncate sma_contact_submissions,sma_contact_limits,sma_contact_installations;
 perform sma_claim_contact(repeat('a',64),repeat('b',64),repeat('c',64),repeat('d',64));
 perform sma_finish_contact(repeat('a',64),true,'fixture-retained');
end $$;
reset role;
