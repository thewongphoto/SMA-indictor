-- Real PostgreSQL lifecycle/summary tests, using fictional addresses only.
set role anon;
do $$ begin
 begin perform count(*) from sma_contact_addresses; raise exception 'Registry exposed';
 exception when insufficient_privilege then null; end;
 begin perform sma_prepare_contact('','','','','','','',''); raise exception 'Lifecycle RPC exposed';
 exception when insufficient_privilege then null; end;
 begin perform sma_contact_message('', '{}'::jsonb); raise exception 'Message exposed';
 exception when insufficient_privilege then null; end;
end $$;
reset role;
set role service_role;
do $$
declare result jsonb; frozen jsonb; changed text; revision bigint;
begin
 if (sma_contact_status()->>'protocol')::integer<>2 then raise exception 'Protocol missing'; end if;
 -- The retained v1 submission has no recoverable address; don't claim it is listed.
 if sma_prepare_contact(repeat('a',64),repeat('b',64),repeat('c',64),repeat('d',64),'old@example.com','save','android','0.17.0')->>'action'<>'expired' then raise exception 'Hash-only acceptance was treated as a complete address record'; end if;
 result:=sma_prepare_contact(repeat('1',64),repeat('9',64),repeat('2',64),repeat('8',64),'first@example.com','save','android','0.17.0');
 if result->'event'->>'action'<>'add' or result->'event'->>'source'<>'android' then raise exception 'Add/source missing: %',result; end if;
 if jsonb_array_length(result->'event'->'records')<>1 then raise exception 'Projected add missing'; end if;
 if (select count(*) from sma_contact_addresses)<>0 then raise exception 'Unaccepted email entered active registry'; end if;
 frozen:=sma_contact_message(repeat('1',64),'{"text":"first frozen template"}'::jsonb);
 if sma_contact_message(repeat('1',64),'{"text":"new template"}'::jsonb)<>frozen then raise exception 'Retry payload changed'; end if;
 if sma_prepare_contact(repeat('3',64),repeat('9',64),repeat('4',64),repeat('8',64),'next@example.com','save','android','0.17.0')->>'action'<>'pending_change' then raise exception 'Uncertain change was overtaken'; end if;
 perform sma_finish_contact(repeat('1',64),true,'fixture-add');
 if sma_prepare_contact(repeat('1',64),repeat('9',64),repeat('2',64),repeat('8',64),'first@example.com','save','web','9.0')->>'action'<>'accepted' then raise exception 'Accepted change resent'; end if;
 if sma_prepare_contact(repeat('1',64),repeat('9',64),repeat('2',64),repeat('8',64),'first@example.com','remove','android','0.17.0')->>'action'<>'conflict' then raise exception 'Operation mutation allowed'; end if;
 if sma_prepare_contact(repeat('5',64),repeat('9',64),repeat('2',64),repeat('8',64),'first@example.com','save','android','0.17.0')->>'action'<>'unchanged' then raise exception 'Same address resent'; end if;
 -- A second installation using the same address remains independent.
 result:=sma_prepare_contact(repeat('6',64),repeat('7',64),repeat('2',64),repeat('6',64),'first@example.com','save','ios-web','0.17.0');
 perform sma_finish_contact(repeat('6',64),true,'fixture-ios');
 result:=sma_prepare_contact(repeat('3',64),repeat('9',64),repeat('4',64),repeat('8',64),'next@example.com','save','android','0.17.0');
 if result->'event'->>'action'<>'modify' or result->'event'->>'before'<>'first@example.com' then raise exception 'Modify incorrect: %',result; end if;
 if (select count(*) from jsonb_array_elements(result->'event'->'records') row where (row->>'active')::boolean)<>2 then raise exception 'Other installation lost from summary'; end if;
 if not exists(select 1 from jsonb_array_elements(result->'event'->'records') row where row->>'email'='first@example.com' and not(row->>'active')::boolean and row->>'last_action'='modify') then raise exception 'Replaced address missing from removed summary'; end if;
 changed:=result->'event'->>'changed_at';
 perform sma_finish_contact(repeat('3',64),false,null,403);
 update sma_contact_submissions set attempted_at=now()-interval '1 minute' where id=repeat('3',64);
 result:=sma_prepare_contact(repeat('3',64),repeat('9',64),repeat('4',64),repeat('8',64),'next@example.com','save','web','9.0');
 if result->'event'->>'changed_at'<>changed or result->'event'->>'source'<>'android' or result->'event'->>'version'<>'0.17.0' then raise exception 'Retry metadata was not frozen'; end if;
 perform sma_finish_contact(repeat('3',64),true,'fixture-modify');
 result:=sma_prepare_contact(repeat('b',64),repeat('9',64),repeat('2',64),repeat('8',64),'first@example.com','remove','android','0.17.0');
 if result->>'action'<>'stale' then raise exception 'Stale removal changed another address'; end if;
 result:=sma_prepare_contact(repeat('c',64),repeat('9',64),repeat('4',64),repeat('8',64),'next@example.com','remove','android','0.17.0');
 if result->'event'->>'action'<>'remove' or result->'event'->'after'<>'null'::jsonb then raise exception 'Remove incorrect'; end if;
 perform sma_finish_contact(repeat('c',64),true,'fixture-remove');
 if exists(select 1 from sma_contact_addresses where install_hash=repeat('9',64) and active) then raise exception 'Removed address still active'; end if;
 if (select count(*) from sma_contact_addresses where active)<>1 then raise exception 'Removal affected another installation'; end if;
 if sma_prepare_contact(repeat('d',64),repeat('9',64),repeat('4',64),repeat('8',64),'next@example.com','remove','android','0.17.0')->>'action'<>'unchanged' then raise exception 'Repeated removal resent'; end if;
 -- Hourly fixture quotas are reset only inside this isolated test database.
 delete from sma_contact_limits;
 result:=sma_prepare_contact(repeat('e',64),repeat('9',64),repeat('2',64),repeat('8',64),'first@example.com','save','android','0.17.0');
 if result->'event'->>'action'<>'add' then raise exception 'Re-add was not an add'; end if;
 perform sma_finish_contact(repeat('e',64),true,'fixture-readd');
 if (select count(*) from sma_contact_addresses where install_hash=repeat('9',64) and active)<>1 then raise exception 'Re-add duplicate rows'; end if;
 -- A failed older operation must never overwrite a later accepted change.
 result:=sma_prepare_contact(repeat('f',64),repeat('9',64),repeat('5',64),repeat('8',64),'failed@example.com','save','android','0.17.0');
 perform sma_finish_contact(repeat('f',64),false,null,403);
 result:=sma_prepare_contact(repeat('0',64),repeat('9',64),repeat('a',64),repeat('8',64),'newer@example.com','save','android','0.17.0');
 perform sma_finish_contact(repeat('0',64),true,'fixture-newer');
 if sma_prepare_contact(repeat('f',64),repeat('9',64),repeat('5',64),repeat('8',64),'failed@example.com','save','android','0.17.0')->>'action'<>'expired' then raise exception 'Stale failed operation was replayed'; end if;
 -- Removing a legacy locally saved address imports only its removal history.
 update sma_contact_submissions set created_at=now()-interval '25 hours' where id=repeat('1',64);
 result:=sma_prepare_contact(repeat('2',64),repeat('3',64),repeat('d',64),repeat('6',64),'legacy@example.com','remove','ios-web','0.17.0');
 perform sma_finish_contact(repeat('2',64),true,'fixture-legacy-remove');
 if not exists(select 1 from sma_contact_addresses where email='legacy@example.com' and not active and last_action='remove') then raise exception 'Legacy removal missing'; end if;
 if exists(select 1 from sma_contact_submissions where id=repeat('1',64) and (event?'records' or message is not null)) then raise exception 'Expired bulk roster was retained'; end if;
 if not exists(select 1 from sma_contact_submissions where id=repeat('1',64) and event->>'action'='add') then raise exception 'Snapshot cleanup deleted change history'; end if;
end $$;
reset role;
