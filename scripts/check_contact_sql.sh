#!/usr/bin/env bash
# Isolated PostgreSQL integration checks. No production database or email service.
set -euo pipefail
cd "$(dirname "$0")/.."
container="sma-contact-check-$$"
trap 'docker rm -f "$container" >/dev/null 2>&1 || true' EXIT
docker run --detach --rm --name "$container" -e POSTGRES_HOST_AUTH_METHOD=trust \
  postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065 >/dev/null
for attempt in {1..60}; do
  if docker exec "$container" pg_isready -h 127.0.0.1 -U postgres >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec -i "$container" psql -U postgres -v ON_ERROR_STOP=1 <<'SQL'
create role anon;
create role authenticated;
create role service_role bypassrls;
SQL
docker exec -i "$container" psql -U postgres -v ON_ERROR_STOP=1 < web/setup/contact.sql
docker exec -i "$container" psql -U postgres -v ON_ERROR_STOP=1 < web/tests/contact.sql
docker exec -i "$container" psql -U postgres -v ON_ERROR_STOP=1 < web/tests/contact-lifecycle.sql
# Applying the optional migration again must preserve existing accepted records.
docker exec -i "$container" psql -U postgres -v ON_ERROR_STOP=1 < web/setup/contact.sql
docker exec -i "$container" psql -U postgres -v ON_ERROR_STOP=1 <<'SQL'
do $$ begin
 if not exists(select 1 from sma_contact_submissions where id=repeat('a',64) and state='accepted')
 or not exists(select 1 from sma_contact_addresses where email='newer@example.com' and active) then
  raise exception 'Migration rerun lost accepted submissions';
 end if;
end $$;
SQL
echo 'PASS: PostgreSQL add/modify/remove, source/version snapshots, frozen payloads, stale retries, rates, restricted registry and idempotent migration.'
